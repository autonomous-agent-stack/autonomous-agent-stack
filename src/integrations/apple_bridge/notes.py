"""Apple Notes Service.

Provides tools for managing Apple Notes via osascript/JXA.
SECURITY: Only Create and Read operations are allowed.
"""

from __future__ import annotations

import subprocess
import re
from typing import Any


class NotesService:
    """Service for Apple Notes operations.

    SECURITY CONSTRAINTS:
    - ✅ CREATE: Create new notes and append to existing notes
    - ✅ READ: View and export notes
    - ❌ DELETE: Strictly forbidden (to prevent data loss)

    Uses osascript/JXA to interact with Notes.app.
    """

    def append_apple_note(
        self,
        note_name: str,
        content: str,
        folder_name: str = "Notes",
        create_if_missing: bool = True,
    ) -> dict[str, Any]:
        """Append content to an existing Apple Note.

        Args:
            note_name: Name of the note to append to
            content: Content to append
            folder_name: Folder containing the note (default: "Notes")
            create_if_missing: Create note if it doesn't exist (default: True)

        Returns:
            Operation status
        """
        try:
            # Escape quotes in content
            escaped_content = content.replace('"', '\\"').replace("'", "'\\''")
            escaped_note_name = note_name.replace('"', '\\"')

            # Build AppleScript command
            script = f'''
            tell application "Notes"
                tell folder "{folder_name}"
                    try
                        set targetNote to note "{escaped_note_name}"
                        set body of targetNote to (body of targetNote) & "<br><br>{escaped_content}"
                        return "success"
                    on error
                        if {str(create_if_missing).lower()} then
                            make new note with properties {{name:"{escaped_note_name}", body:"{escaped_content}"}}
                            return "created"
                        else
                            error "Note not found"
                        end if
                    end try
                end tell
            end tell
            '''

            # Execute osascript
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                action = "appended" if result.stdout.strip() == "success" else "created"
                return {
                    "status": "success",
                    "message": f"Successfully {action} to note '{note_name}'",
                    "note_name": note_name,
                    "folder": folder_name,
                    "action": action,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout while appending to note",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def create_apple_note(
        self,
        title: str,
        body: str,
        folder_name: str = "Notes",
    ) -> dict[str, Any]:
        """Create a new Apple Note.

        Args:
            title: Note title
            body: Note body/content
            folder_name: Folder to create note in (default: "Notes")

        Returns:
            Created note status
        """
        try:
            # Escape quotes
            escaped_title = title.replace('"', '\\"')
            escaped_body = body.replace('"', '\\"')

            script = f'''
            tell application "Notes"
                tell folder "{folder_name}"
                    make new note with properties {{name:"{escaped_title}", body:"{escaped_body}"}}
                end tell
            end tell
            '''

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"Note '{title}' created successfully",
                    "title": title,
                    "folder": folder_name,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout while creating note",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def list_apple_notes(
        self,
        folder_name: str = "Notes",
        limit: int = 50,
    ) -> dict[str, Any]:
        """List notes from Apple Notes.

        Args:
            folder_name: Folder to list notes from (default: "Notes")
            limit: Maximum number of notes to return

        Returns:
            List of notes
        """
        try:
            script = f'''
            tell application "Notes"
                tell folder "{folder_name}"
                    set noteList to {{}}
                    set noteCounter to 0
                    repeat with eachNote in (get every note)
                        if noteCounter ≥ {limit} then exit repeat
                        set noteInfo to {{}}
                        set noteInfo to noteInfo & {{name:name of eachNote}}
                        set noteInfo to noteInfo & {{modification date:(modification date of eachNote as string)}}
                        set end of noteList to noteInfo
                        set noteCounter to noteCounter + 1
                    end repeat
                    return noteList
                end tell
            end tell
            '''

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                # Parse output (simplified)
                notes = self._parse_notes_output(result.stdout)

                return {
                    "status": "success",
                    "count": len(notes),
                    "notes": notes,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout while listing notes",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _parse_notes_output(self, output: str) -> list[dict[str, Any]]:
        """Parse AppleScript note list output."""
        output = output.strip()
        if not output:
            return []

        records = self._split_records(output, anchor_key="name")
        notes: list[dict[str, Any]] = []
        for record in records:
            parsed = self._parse_record(record, ["name", "modification date"])
            if not parsed:
                continue
            note: dict[str, Any] = {
                "name": parsed.get("name", ""),
            }
            if parsed.get("modification date"):
                note["modification_date"] = parsed["modification date"]
            notes.append(note)
        return notes

    @staticmethod
    def _split_records(output: str, anchor_key: str) -> list[str]:
        payload = output.strip().strip("{}").strip()
        if not payload:
            return []
        anchor_pattern = re.compile(rf"(?:^|,\s*){re.escape(anchor_key)}:")
        matches = list(anchor_pattern.finditer(payload))
        if not matches:
            return [payload]

        starts = [match.start() for match in matches] + [len(payload)]
        records: list[str] = []
        for index in range(len(starts) - 1):
            segment = payload[starts[index]:starts[index + 1]].lstrip(", ").strip()
            if segment:
                records.append(segment)
        return records

    @staticmethod
    def _parse_record(record: str, keys: list[str]) -> dict[str, str]:
        key_pattern = "|".join(re.escape(key) for key in keys)
        matcher = re.compile(rf"(?:^|,\s*)({key_pattern}):")
        matches = list(matcher.finditer(record))
        if not matches:
            return {}

        parsed: dict[str, str] = {}
        for index, match in enumerate(matches):
            key = match.group(1)
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(record)
            value = record[start:end].strip().strip(",").strip()
            parsed[key] = value.strip('"')
        return parsed
