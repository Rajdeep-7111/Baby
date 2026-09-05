"""Restricted, read-only text-file tool."""

from pathlib import Path
from typing import Any


class FileReaderTool:
    """Reads approved text files located inside the Baby workspace."""

    name = "file_reader"
    description = "Reads a text file from a relative path inside the Baby workspace."
    input_schema: dict[str, Any] = {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}
    _allowed_suffixes = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv"}
    _workspace_root = Path(__file__).resolve().parents[3]

    def execute(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        requested_path = tool_input.get("path")
        if not isinstance(requested_path, str) or not requested_path.strip():
            return {"success": False, "result": None, "error": "'path' must be a non-empty string."}
        path = Path(requested_path)
        if path.is_absolute() or any(part.startswith(".") for part in path.parts):
            return {"success": False, "result": None, "error": "Path must be a safe relative workspace path."}
        if path.suffix.lower() not in self._allowed_suffixes:
            return {"success": False, "result": None, "error": "Only approved text file types may be read."}
        resolved_path = (self._workspace_root / path).resolve()
        if not resolved_path.is_relative_to(self._workspace_root):
            return {"success": False, "result": None, "error": "Path is outside the Baby workspace."}
        if not resolved_path.is_file():
            return {"success": False, "result": None, "error": "File does not exist or is not a regular file."}
        try:
            content = resolved_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            return {"success": False, "result": None, "error": f"Could not read file: {error}"}
        return {"success": True, "result": {"path": str(path), "content": content}, "error": None}
