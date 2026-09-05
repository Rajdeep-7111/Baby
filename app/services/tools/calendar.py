"""Google Calendar tool for Baby."""

from __future__ import annotations

import datetime as dt
from typing import Any

from app.services.calendar.service import CalendarService


class CalendarTool:
    """Expose Google Calendar operations through Baby's tool system."""

    name = "calendar"

    description = (
        "Read today's calendar events and create calendar events."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "today",
                    "date",
                    "create",
                ],
            },
            "title": {
                "type": "string",
            },
            "start": {
                "type": "string",
                "description": (
                    "Timezone-aware ISO datetime."
                ),
            },
            "end": {
                "type": "string",
                "description": (
                    "Timezone-aware ISO datetime."
                ),
            },
            "description": {
                "type": "string",
            },
        },
        "required": ["operation"],
    }

    def __init__(
        self,
        service: CalendarService | None = None,
    ) -> None:
        self._service = (
            service
            if service is not None
            else CalendarService()
        )

    def execute(
        self,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        operation = tool_input.get("operation")

        try:
            # -------------------------------------------------
            # Today's events
            # -------------------------------------------------

            if operation == "today":
                events = (
                    self._service.get_today_events()
                )

                return {
                    "success": True,
                    "result": {
                        "count": len(events),
                        "events": events,
                    },
                    "error": None,
                }

            # -------------------------------------------------
            # Events for a requested date
            # -------------------------------------------------

            if operation == "date":
                date_string = str(tool_input.get("date", "")).strip()
                if not date_string:
                    return {"success": False, "result": None, "error": "Calendar date is required."}

                target_date = dt.date.fromisoformat(date_string)
                events = self._service.get_events_for_date(target_date)

                after_time = str(tool_input.get("after_time", "")).strip()
                if after_time:
                    threshold = dt.time.fromisoformat(after_time)
                    filtered = []
                    for event in events:
                        start = event.get("start", "")
                        if not start:
                            continue
                        try:
                            event_dt = dt.datetime.fromisoformat(start)
                            if event_dt.timetz().replace(tzinfo=None) >= threshold:
                                filtered.append(event)
                        except (ValueError, TypeError):
                            continue
                    events = filtered

                return {
                    "success": True,
                    "result": {
                        "date": date_string,
                        "count": len(events),
                        "events": events,
                        "after_time": after_time or None,
                    },
                    "error": None,
                }

            # -------------------------------------------------
            # Events for a requested date
            # -------------------------------------------------

            if operation == "date":
                date_string = str(tool_input.get("date", "")).strip()
                if not date_string:
                    return {"success": False, "result": None, "error": "Calendar date is required."}

                target_date = dt.date.fromisoformat(date_string)
                events = self._service.get_events_for_date(target_date)

                after_time = str(tool_input.get("after_time", "")).strip()
                if after_time:
                    threshold = dt.time.fromisoformat(after_time)
                    filtered = []
                    for event in events:
                        start = event.get("start", "")
                        if not start:
                            continue
                        try:
                            event_dt = dt.datetime.fromisoformat(start)
                            if event_dt.timetz().replace(tzinfo=None) >= threshold:
                                filtered.append(event)
                        except (ValueError, TypeError):
                            continue
                    events = filtered

                return {
                    "success": True,
                    "result": {
                        "date": date_string,
                        "count": len(events),
                        "events": events,
                        "after_time": after_time or None,
                    },
                    "error": None,
                }

            # -------------------------------------------------
            # Create event
            # -------------------------------------------------

            if operation == "create":
                title = str(
                    tool_input.get("title", "")
                ).strip()

                start_string = str(
                    tool_input.get("start", "")
                ).strip()

                end_string = str(
                    tool_input.get("end", "")
                ).strip()

                description = tool_input.get(
                    "description"
                )

                if not title:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Calendar event title "
                            "is required."
                        ),
                    }

                if not start_string:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Calendar event start "
                            "time is required."
                        ),
                    }

                if not end_string:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Calendar event end "
                            "time is required."
                        ),
                    }

                # Convert ISO strings into timezone-aware
                # datetime objects.
                start = dt.datetime.fromisoformat(
                    start_string.replace(
                        "Z",
                        "+00:00",
                    )
                )

                end = dt.datetime.fromisoformat(
                    end_string.replace(
                        "Z",
                        "+00:00",
                    )
                )

                if start.tzinfo is None:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Start time must include "
                            "timezone information."
                        ),
                    }

                if end.tzinfo is None:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "End time must include "
                            "timezone information."
                        ),
                    }

                created = (
                    self._service.create_event(
                        title=title,
                        start=start,
                        end=end,
                        description=description,
                    )
                )

                created_start = created.get(
                    "start",
                    {},
                )

                return {
                    "success": True,
                    "result": {
                        "id": created.get("id"),
                        "title": created.get(
                            "summary",
                            title,
                        ),
                        "start": created_start.get(
                            "dateTime",
                            created_start.get(
                                "date"
                            ),
                        ),
                        "description": created.get(
                            "description"
                        ),
                    },
                    "error": None,
                }

            return {
                "success": False,
                "result": None,
                "error": (
                    f"Unknown calendar operation: "
                    f"{operation}"
                ),
            }

        except Exception as error:
            return {
                "success": False,
                "result": None,
                "error": (
                    f"Calendar operation failed: "
                    f"{error}"
                ),
            }