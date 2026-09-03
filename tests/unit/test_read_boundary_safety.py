"""Structural guardrails for the new offline-only modules."""

import ast
import inspect
from pathlib import Path

from knee_rig.motion.driver import fake_transport, read_errors, read_models, reader, transport


def test_offline_boundary_has_no_forbidden_dependencies_writes_or_loops() -> None:
    forbidden = {
        "serial",
        "minimalmodbus",
        "pymodbus",
        "socket",
        "httpx",
        "requests",
        "fastapi",
        "flask",
        "PySide6",
        "RPi",
        "gpiozero",
        "cv2",
        "picamera",
    }
    for module in (fake_transport, read_errors, read_models, reader, transport):
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] not in forbidden for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden
                assert "gui" not in (node.module or "").split(".")
                assert "reference" not in (node.module or "").split(".")
                assert "state_machine" not in (node.module or "").split(".")
                assert "service" not in (node.module or "").split(".")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert not node.name.startswith("write")
                assert node.name != "execute"
            assert not isinstance(node, ast.While)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"sleep", "start", "Thread", "Popen"}


def test_reader_is_symbolic_and_gui_has_no_reader_integration() -> None:
    public_methods = {
        name
        for name, _ in inspect.getmembers(reader.ReadOnlyServoReader, inspect.isfunction)
        if not name.startswith("_")
    }
    assert public_methods == {"read", "snapshot"}
    assert tuple(inspect.signature(reader.ReadOnlyServoReader.read).parameters) == (
        "self",
        "symbol",
    )
    root = Path(__file__).resolve().parents[2]
    for path in (root / "src/knee_rig/gui").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "ReadOnlyServoReader" not in text
        assert "motion.diagnostics" not in text
        tree = ast.parse(text)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not any(
            name == forbidden or name.startswith(f"{forbidden}.")
            for name in imports
            for forbidden in ("serial", "minimalmodbus", "pymodbus")
        )
