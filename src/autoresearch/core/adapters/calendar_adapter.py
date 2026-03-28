from __future__ import annotations

from typing import Any

from integrations.apple_bridge.calendar import CalendarService

from autoresearch.core.adapters.contracts import (
    CalendarAdapter,
    CalendarEventRead,
    CalendarQuery,
    CalendarQueryResultRead,
    CapabilityDomain,
    CapabilityProviderDescriptorRead,
    ProviderStatus,
)


class AppleCalendarAdapter(CalendarAdapter):
    def __init__(self, service: CalendarService | None = None) -> None:
        self._service = service or CalendarService()

    def describe(self) -> CapabilityProviderDescriptorRead:
        return CapabilityProviderDescriptorRead(
            provider_id="apple-calendar",
            domain=CapabilityDomain.CALENDAR,
            display_name="Apple Calendar",
            capabilities=["read_today", "read_range"],
            metadata={"transport": "host_bridge"},
        )

    def query_events(self, query: CalendarQuery) -> CalendarQueryResultRead:
        if query.window == "range":
            response = self._service.read_calendar_range(
                start_date=query.start_date or "",
                end_date=query.end_date or "",
                calendar_name=query.calendar_name,
            )
        else:
            response = self._service.read_calendar_today(calendar_name=query.calendar_name)
        return self._normalize_response(response)

    def _normalize_response(self, response: dict[str, Any]) -> CalendarQueryResultRead:
        status = ProviderStatus.AVAILABLE if response.get("status") == "success" else ProviderStatus.DEGRADED
        events: list[CalendarEventRead] = []
        for item in response.get("events", []):
            if not isinstance(item, dict):
                continue
            events.append(
                CalendarEventRead(
                    summary=str(item.get("summary") or ""),
                    start_at=_safe_str(item.get("start_date") or item.get("startDate")),
                    end_at=_safe_str(item.get("end_date") or item.get("endDate")),
                    location=_safe_str(item.get("location")),
                    metadata={},
                )
            )
        return CalendarQueryResultRead(
            provider_id="apple-calendar",
            status=status,
            events=events,
            raw_count=int(response.get("count", len(events))),
            error=_safe_str(response.get("error")),
            metadata={key: value for key, value in response.items() if key not in {"status", "events", "count", "error"}},
        )


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
