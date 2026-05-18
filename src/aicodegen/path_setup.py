from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def merge_windows_path_entries(existing_path: str, new_entry: str) -> tuple[str, bool]:
    existing_parts = [part for part in existing_path.split(";") if part]
    normalized_existing = {_normalize_windows_path(part) for part in existing_parts}
    normalized_new = _normalize_windows_path(new_entry)
    if normalized_new in normalized_existing:
        return existing_path, False
    merged_parts = [new_entry, *existing_parts] if existing_parts else [new_entry]
    return ";".join(merged_parts), True


class PathSetupService:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def ensure_cli_on_user_path(self) -> dict[str, Any]:
        scripts_dir = self.workspace / ".venv" / "Scripts"
        cli_path = scripts_dir / "aicodegen.exe"

        if os.name != "nt":
            return {
                "status": "unsupported_os",
                "path_added": False,
                "target": str(scripts_dir),
            }
        if not cli_path.exists():
            return {
                "status": "cli_not_found",
                "path_added": False,
                "target": str(scripts_dir),
            }

        try:
            import winreg
        except ImportError:
            return {
                "status": "winreg_unavailable",
                "path_added": False,
                "target": str(scripts_dir),
            }

        scripts_dir_str = str(scripts_dir)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            try:
                current_path, value_type = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current_path, value_type = "", winreg.REG_EXPAND_SZ

            updated_path, changed = merge_windows_path_entries(current_path, scripts_dir_str)
            if not changed:
                return {
                    "status": "already_present",
                    "path_added": False,
                    "target": scripts_dir_str,
                }

            winreg.SetValueEx(key, "Path", 0, value_type, updated_path)

        return {
            "status": "added",
            "path_added": True,
            "target": scripts_dir_str,
            "note": "Open a new terminal session to use the updated PATH.",
        }


def _normalize_windows_path(value: str) -> str:
    return str(Path(value)).rstrip("\\/").lower()
