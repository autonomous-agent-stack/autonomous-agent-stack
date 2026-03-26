"""Google Calendar API Client.

Provides tools for creating and managing calendar events.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency guard
    build = None
    _GOOGLE_API_IMPORT_ERROR = exc

    class HttpError(Exception):
        """Fallback HttpError when google-api-python-client is unavailable."""

else:
    _GOOGLE_API_IMPORT_ERROR = None

from .oauth import OAuthManager


class GoogleCalendarClient:
    """Client for Google Calendar API operations.

    Provides the following tools:
    - create_google_event: Create a new calendar event
    - list_google_events: List events in a time range
    """

    def __init__(self, oauth_manager: OAuthManager | None = None) -> None:
        self.oauth_manager = oauth_manager or OAuthManager()
        self._service = None

    @property
    def service(self):
        """Lazy-load Google Calendar service."""
        if self._service is None:
            if build is None:
                raise RuntimeError(
                    "google-api-python-client is required for Google Calendar integration. "
                    "Install it via `pip install google-api-python-client`."
                ) from _GOOGLE_API_IMPORT_ERROR
            credentials = self.oauth_manager.get_credentials()
            self._service = build("calendar", "v3", credentials=credentials)
        return self._service

    def create_google_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Create a new Google Calendar event.

        Args:
            summary: Event title/summary
            start_time: ISO 8601 datetime string (e.g., "2026-03-26T10:00:00")
            end_time: ISO 8601 datetime string
            description: Event description (optional)
            location: Event location (optional)
            attendees: List of attendee email addresses (optional)
            calendar_id: Calendar ID (default: "primary")

        Returns:
            Created event data

        Raises:
            HttpError: If API call fails
        """
        event = {
            "summary": summary,
            "start": {
                "dateTime": start_time,
                "timeZone": "Asia/Shanghai",
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "Asia/Shanghai",
            },
        }

        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        try:
            created_event = (
                self.service.events().insert(calendarId=calendar_id, body=event).execute()
            )
            return {
                "status": "success",
                "event_id": created_event["id"],
                "html_link": created_event["htmlLink"],
                "summary": created_event["summary"],
                "start": created_event["start"]["dateTime"],
                "end": created_event["end"]["dateTime"],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }

    def list_google_events(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        max_results: int = 10,
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """List Google Calendar events in a time range.

        Args:
            start_time: ISO 8601 datetime string (default: now)
            end_time: ISO 8601 datetime string (default: 7 days from now)
            max_results: Maximum number of events to return
            calendar_id: Calendar ID (default: "primary")

        Returns:
            List of events
        """
        if not start_time:
            start_time = datetime.utcnow().isoformat() + "Z"
        if not end_time:
            end_time = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start_time,
                    timeMax=end_time,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            return {
                "status": "success",
                "count": len(events),
                "events": [
                    {
                        "id": event["id"],
                        "summary": event.get("summary", "No Title"),
                        "start": event["start"].get("dateTime", event["start"].get("date")),
                        "end": event["end"].get("dateTime", event["end"].get("date")),
                        "location": event.get("location"),
                    }
                    for event in events
                ],
            }
        except HttpError as error:
            return {
                "status": "error",
                "error": str(error),
                "error_code": error.status_code,
            }
