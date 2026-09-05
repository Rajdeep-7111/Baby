"""Controlled Windows desktop interaction tool for Baby."""

from __future__ import annotations

import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any


class DesktopTool:
    """Perform a small, explicit set of safe desktop operations."""

    name = "desktop"
    description = (
        "Control common Windows desktop operations: open allowlisted apps, "
        "open URLs/files/folders, type text, press keyboard shortcuts, and "
        "take screenshots."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["open_app", "open_url", "open_path", "type_text", "hotkey", "screenshot"],
            },
            "target": {"type": "string"},
            "text": {"type": "string"},
            "keys": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["operation"],
    }

    _APP_COMMANDS = {
        "chrome": ["cmd", "/c", "start", "", "chrome"],
        "google chrome": ["cmd", "/c", "start", "", "chrome"],
        "edge": ["cmd", "/c", "start", "", "msedge"],
        "microsoft edge": ["cmd", "/c", "start", "", "msedge"],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "file explorer": ["explorer.exe"],
        "explorer": ["explorer.exe"],
        "command prompt": ["cmd.exe"],
        "cmd": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "terminal": ["wt.exe"],
        "windows terminal": ["wt.exe"],
        "vscode": ["code"],
        "visual studio code": ["code"],
    }

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        operation = str(tool_input.get("operation", "")).strip().lower()

        try:
            if operation == "open_app":
                return self._open_app(str(tool_input.get("target", "")))
            if operation == "open_url":
                return self._open_url(str(tool_input.get("target", "")))
            if operation == "open_path":
                return self._open_path(str(tool_input.get("target", "")))
            if operation == "type_text":
                return self._type_text(str(tool_input.get("text", "")))
            if operation == "hotkey":
                keys = tool_input.get("keys", [])
                return self._hotkey(keys if isinstance(keys, list) else [])
            if operation == "screenshot":
                return self._screenshot()

            return {"success": False, "result": None, "error": f"Unsupported desktop operation: {operation}"}
        except Exception as error:
            return {"success": False, "result": None, "error": f"Desktop operation failed: {error}"}

    def _open_app(self, target: str) -> dict[str, Any]:
        key = target.strip().lower()
        command = self._APP_COMMANDS.get(key)
        if command is None:
            return {"success": False, "result": None, "error": f"App '{target}' is not in Baby's desktop allowlist."}
        subprocess.Popen(command)
        return {"success": True, "result": f"Opened {target}.", "error": None}

    @staticmethod
    def _open_url(target: str) -> dict[str, Any]:
        url = target.strip()
        if not url.startswith(("http://", "https://")):
            return {"success": False, "result": None, "error": "Only http:// and https:// URLs are allowed."}
        webbrowser.open(url)
        return {"success": True, "result": f"Opened {url}.", "error": None}

    @staticmethod
    def _open_path(target: str) -> dict[str, Any]:
        path = os.path.expandvars(os.path.expanduser(target.strip()))
        if not path:
            return {"success": False, "result": None, "error": "No path was provided."}
        if not os.path.exists(path):
            return {"success": False, "result": None, "error": f"Path does not exist: {path}"}
        os.startfile(path)  # type: ignore[attr-defined]
        return {"success": True, "result": f"Opened {path}.", "error": None}

    @staticmethod
    def _require_pyautogui():
        try:
            import pyautogui
        except ImportError as error:
            raise RuntimeError("pyautogui is required for typing, hotkeys, and screenshots. Install it with: pip install pyautogui") from error
        return pyautogui

    def _type_text(self, text: str) -> dict[str, Any]:
        if not text:
            return {"success": False, "result": None, "error": "No text was provided."}
        pyautogui = self._require_pyautogui()
        pyautogui.write(text, interval=0.01)
        return {"success": True, "result": "Typed the requested text.", "error": None}

    def _hotkey(self, keys: list[Any]) -> dict[str, Any]:
        normalized = [str(key).strip().lower() for key in keys if str(key).strip()]
        if not normalized:
            return {"success": False, "result": None, "error": "No keyboard keys were provided."}
        pyautogui = self._require_pyautogui()
        pyautogui.hotkey(*normalized)
        return {"success": True, "result": f"Pressed {' + '.join(normalized)}.", "error": None}

    def _screenshot(self) -> dict[str, Any]:
        pyautogui = self._require_pyautogui()
        directory = Path.home() / "Pictures" / "Baby"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
        pyautogui.screenshot(str(path))
        return {"success": True, "result": f"Screenshot saved to {path}.", "error": None}
