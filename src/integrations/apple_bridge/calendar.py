"""Apple Calendar Service.

Provides tools for reading Apple Calendar events via osascript.
SECURITY: Only Read operations are allowed.
"""

from __future__ import annotations

import subprocess
import re
from datetime import datetime, timedelta
from typing import Any


class CalendarService:
    """Service for Apple Calendar operations.

    SECURITY CONSTRAINTS:
    - ❌ CREATE: Not exposed via bridge (use Google Calendar instead)
    - ✅ READ: View calendar events
    - ❌ DELETE: Strictly forbidden

    Uses osascript to interact with Calendar.app.
    """

    def read_calendar_today(
        self,
        calendar_name: str | None = None,
    ) -> dict[str, Any]:
        """Read today's calendar events.

        Args:
            calendar_name: Specific calendar to read (optional, reads all if not specified)

        Returns:
            List of today's events
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

            # Build AppleScript
            if calendar_name:
                calendar_filter = f'calendars whose name is "{calendar_name}"'
            else:
                calendar_filter = "calendars"

            script = f'''
            tell application "Calendar"
                set todayStart to current date
                set hours of todayStart to 0
                set minutes of todayStart to 0
                set seconds of todayStart to 0

                set todayEnd to todayStart + (1 * days)

                set eventList to {{}}

                repeat with eachCalendar in {calendar_filter}
                    repeat with eachEvent in (every event of eachCalendar whose start date ≥ todayStart and start date < todayEnd)
                        set eventInfo to {{}}
                        set eventInfo to eventInfo & {{summary:summary of eachEvent}}
                        set eventInfo to eventInfo & {{startDate:(start date of eachEvent as string)}}
                        set eventInfo to eventInfo & {{endDate:(end date of eachEvent as string)}}
                        try
                            set eventInfo to eventInfo & {{location:location of eachEvent}}
                        end try
                        set end of eventList to eventInfo
                    end repeat
                end repeat

                return eventList
            end tell
            '''

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                events = self._parse_events_output(result.stdout)

                return {
                    "status": "success",
                    "date": today,
                    "count": len(events),
                    "events": events,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout while reading calendar",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def read_calendar_range(
        self,
        start_date: str,
        end_date: str,
        calendar_name: str | None = None,
    ) -> dict[str, Any]:
        """Read calendar events in a date range.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            calendar_name: Specific calendar to read (optional)

        Returns:
            List of events in the range
        """
        try:
            if calendar_name:
                calendar_filter = f'calendars whose name is "{calendar_name}"'
            else:
                calendar_filter = "calendars"

            script = f'''
            tell application "Calendar"
                set rangeStart to date "{start_date}"
                set rangeEnd to date "{end_date}"

                set eventList to {{}}

                repeat with eachCalendar in {calendar_filter}
                    repeat with eachEvent in (every event of eachCalendar whose start date ≥ rangeStart and start date ≤ rangeEnd)
                        set eventInfo to {{}}
                        set eventInfo to eventInfo & {{summary:summary of eachEvent}}
                        set eventInfo to eventInfo & {{startDate:(start date of eachEvent as string)}}
                        set eventInfo to eventInfo & {{endDate:(end date of eachEvent as string)}}
                        try
                            set eventInfo to eventInfo & {{location:location of eachEvent}}
                        end try
                        set end of eventList to eventInfo
                    end repeat
                end repeat

                return eventList
            end tell
            '''

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=20,
            )

            if result.returncode == 0:
                events = self._parse_events_output(result.stdout)

                return {
                    "status": "success",
                    "start_date": start_date,
                    "end_date": end_date,
                    "count": len(events),
                    "events": events,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Timeout while reading calendar",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def _parse_events_output(self, output: str) -> list[dict[str, Any]]:
        """Parse AppleScript event list output."""
        output = output.strip()
        if not output:
            return []

        records = self._split_records(output, anchor_key="summary")
        events: list[dict[str, Any]] = []
        key_map = {
            "summary": "summary",
            "startDate": "start_date",
            "endDate": "end_date",
            "location": "location",
        }
        for record in records:
            parsed = self._parse_record(record, list(key_map.keys()))
            if not parsed:
                continue
            event = {target: parsed.get(source, "") for source, target in key_map.items() if parsed.get(source)}
            if event:
                events.append(event)
        return events

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
