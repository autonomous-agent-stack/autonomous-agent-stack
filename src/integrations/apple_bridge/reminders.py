"""Apple Reminders Service.

Provides tools for managing Apple Reminders via osascript/shortcuts.
SECURITY: Only Create and Read operations are allowed.
"""

from __future__ import annotations

import subprocess
import json
from typing import Any


class RemindersService:
    """Service for Apple Reminders operations.

    SECURITY CONSTRAINTS:
    - ✅ CREATE: Add new reminders
    - ✅ READ: List and view reminders
    - ❌ DELETE: Strictly forbidden (to prevent data loss)

    Uses osascript to interact with Reminders.app.
    """

    def add_apple_reminder(
        self,
        title: str,
        notes: str | None = None,
        due_date: str | None = None,
        list_name: str = "Reminders",
    ) -> dict[str, Any]:
        """Add a new reminder to Apple Reminders.

        Args:
            title: Reminder title
            notes: Reminder notes (optional)
            due_date: Due date in ISO format (optional)
            list_name: Reminders list name (default: "Reminders")

        Returns:
            Created reminder status
        """
        try:
            # Build AppleScript command
            script_parts = [
                'tell application "Reminders"',
                f'  tell list "{list_name}"',
                f'    make new reminder with properties {{name:"{title}"',
            ]

            if notes:
                # Escape quotes in notes
                escaped_notes = notes.replace('"', '\\"')
                script_parts.append(f', body:"{escaped_notes}"')

            if due_date:
                # Parse ISO date and convert to AppleScript date format
                script_parts.append(f', due date:date "{due_date}"')

            script_parts.append('}')
            script_parts.append('  end tell')
            script_parts.append('end tell')

            script = '\n'.join(script_parts)

            # Execute osascript
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": f"Reminder '{title}' added successfully",
                    "title": title,
                    "list": list_name,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout while adding reminder",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def list_apple_reminders(
        self,
        list_name: str = "Reminders",
        include_completed: bool = False,
    ) -> dict[str, Any]:
        """List reminders from Apple Reminders.

        Args:
            list_name: Reminders list name (default: "Reminders")
            include_completed: Whether to include completed reminders

        Returns:
            List of reminders
        """
        try:
            # Build AppleScript to get reminders
            script = f'''
            tell application "Reminders"
                tell list "{list_name}"
                    set reminderList to {{}}
                    repeat with eachReminder in (get every reminder)
                        set reminderInfo to {{}}
                        set reminderInfo to reminderInfo & {{name:name of eachReminder}}
                        set reminderInfo to reminderInfo & {{body:body of eachReminder}}
                        set reminderInfo to reminderInfo & {{completed:completed of eachReminder}}
                        try
                            set reminderInfo to reminderInfo & {{due date:(due date of eachReminder as string)}}
                        end try
                        set end of reminderList to reminderInfo
                    end repeat
                    return reminderList
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
                # Parse AppleScript record output
                # This is a simplified parser; real implementation would need more robust parsing
                reminders = self._parse_applescript_records(result.stdout)

                if not include_completed:
                    reminders = [r for r in reminders if not r.get("completed", False)]

                return {
                    "status": "success",
                    "count": len(reminders),
                    "reminders": reminders,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout while listing reminders",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _parse_applescript_records(self, output: str) -> list[dict[str, Any]]:
        """Parse AppleScript record output into Python dicts.

        This is a simplified parser. Real implementation would need more robust parsing.
        """
        # Simplified parsing - in production, use proper AppleScript record parser
        # For now, return empty list as this requires more complex implementation
        reminders = []

        # TODO: Implement proper AppleScript record parsing
        # Alternative: Use JSON via shortcuts or JXA (JavaScript for Automation)

        return reminders
