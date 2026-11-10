"""Shared fixtures.

Every test session runs with QSettings redirected to an INI file in a temp directory, so no test
(MainWindow stores geometry, toolbar state and recent files) can write the user's real
preferences (macOS plist). Per-module copies of this fixture still work; they just override the
path for their module.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings


@pytest.fixture(scope="session", autouse=True)
def _isolated_qsettings(tmp_path_factory):
    d = tmp_path_factory.mktemp("qsettings")
    old_fmt = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
        QSettings.setPath(QSettings.Format.IniFormat, scope, str(d))
    yield d
    QSettings.setDefaultFormat(old_fmt)
