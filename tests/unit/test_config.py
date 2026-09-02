"""Configuration is layered, strict, and fail-closed."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from knee_rig.common.config import ConfigValidationError, load_config


class ConfigTests(unittest.TestCase):
    def _write(self, directory: Path, name: str, text: str) -> Path:
        path = directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_safe_defaults(self) -> None:
        config = load_config()
        self.assertTrue(config.features.simulation)
        self.assertFalse(config.features.allow_servo_enable)
        self.assertFalse(config.features.allow_motion)
        self.assertFalse(config.features.allow_homing)
        self.assertFalse(config.features.allow_persistent_parameter_write)
        self.assertFalse(config.features.calibration_verified)
        self.assertEqual(config.calibration.position_units_per_joint_degree, 0.0)
        self.assertEqual(config.serial.device, "")
        self.assertEqual(config.serial.byteorder_32, "unverified")

    def test_valid_local_override_layers_after_shared(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            shared = self._write(
                directory,
                "common.toml",
                '[logging]\nlevel = "WARNING"\n',
            )
            local = self._write(
                directory,
                "common.local.toml",
                '[logging]\nlevel = "DEBUG"\ndirectory = "logs"\n',
            )
            config = load_config(shared_paths=[shared], local_paths=[local])
        self.assertEqual(config.logging.level, "DEBUG")
        self.assertEqual(config.logging.directory, "logs")

    def test_current_common_pi_and_windows_examples_match_the_schema(self) -> None:
        config_directory = Path("config")
        pi = load_config(
            shared_paths=[
                config_directory / "common.example.toml",
                config_directory / "pi.example.toml",
            ]
        )
        windows = load_config(
            shared_paths=[
                config_directory / "common.example.toml",
                config_directory / "windows.example.toml",
            ]
        )
        self.assertTrue(pi.features.simulation)
        self.assertEqual(pi.serial.device, "")
        self.assertTrue(windows.features.simulation)

    def test_missing_optional_local_file_is_allowed(self) -> None:
        config = load_config(local_paths=[Path("does-not-exist.local.toml")])
        self.assertTrue(config.features.simulation)

    def test_missing_required_shared_file_is_rejected(self) -> None:
        with self.assertRaises(ConfigValidationError) as caught:
            load_config(shared_paths=[Path("does-not-exist.toml")])
        self.assertIn("CONFIG_FILE_MISSING", caught.exception.codes)

    def test_invalid_type_is_not_coerced(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            path = self._write(
                Path(raw_directory),
                "bad.toml",
                '[features]\nsimulation = "true"\n',
            )
            with self.assertRaises(ConfigValidationError) as caught:
                load_config(shared_paths=[path])
        self.assertIn("INVALID_TYPE", caught.exception.codes)

    def test_unknown_safety_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            path = self._write(
                Path(raw_directory),
                "bad.toml",
                "[features]\nallow_unreviewed_motion = true\n",
            )
            with self.assertRaises(ConfigValidationError) as caught:
                load_config(shared_paths=[path])
        self.assertIn("UNKNOWN_FIELD", caught.exception.codes)

    def test_persistent_write_capability_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            path = self._write(
                Path(raw_directory),
                "bad.toml",
                "[features]\nallow_persistent_parameter_write = true\n",
            )
            with self.assertRaises(ConfigValidationError) as caught:
                load_config(shared_paths=[path])
        self.assertIn("PERSISTENT_WRITES_UNAVAILABLE", caught.exception.codes)

    def test_missing_and_zero_calibration_remain_unverified(self) -> None:
        config = load_config()
        self.assertEqual(config.calibration.position_units_per_joint_degree, 0.0)
        self.assertFalse(config.features.calibration_verified)

    def test_verified_zero_calibration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            path = self._write(
                Path(raw_directory),
                "bad.toml",
                "[features]\ncalibration_verified = true\n",
            )
            with self.assertRaises(ConfigValidationError) as caught:
                load_config(shared_paths=[path])
        self.assertIn("INVALID_CALIBRATION", caught.exception.codes)

    def test_missing_serial_path_is_valid_in_simulation(self) -> None:
        self.assertEqual(load_config().serial.device, "")

    def test_non_by_id_path_is_rejected_for_real_mode(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            path = self._write(
                Path(raw_directory),
                "bad.toml",
                '[features]\nsimulation = false\n[serial]\ndevice = "/dev/ttyUSB0"\n',
            )
            with self.assertRaises(ConfigValidationError) as caught:
                load_config(shared_paths=[path])
        self.assertIn("NON_BY_ID_SERIAL_DEVICE", caught.exception.codes)
        self.assertIn("REAL_HARDWARE_UNAVAILABLE", caught.exception.codes)

    def test_selected_byte_order_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            path = self._write(
                Path(raw_directory),
                "bad.toml",
                '[serial]\nbyteorder_32 = "little"\n',
            )
            with self.assertRaises(ConfigValidationError) as caught:
                load_config(shared_paths=[path])
        self.assertIn("BYTEORDER_MUST_REMAIN_UNVERIFIED", caught.exception.codes)


if __name__ == "__main__":
    unittest.main()
