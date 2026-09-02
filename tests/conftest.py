"""GUI-test environment configuration with no physical display dependency."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
