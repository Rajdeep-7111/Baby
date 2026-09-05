"""Google Calendar integration for Baby."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build


class CalendarService:
    """Provides read/create access to the user's Google Calendar."""

    SCOPES = [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    def __init__(
        self,
        credentials_path: Path | str = "credentials.json",
        token_path: Path | str = "token.json",
    ) -> None:
        self._credentials_path = Path(credentials_path)
        self._token_path = Path(token_path)
        self._service = self._authenticate()

    def _authenticate(self) -> Resource:
        """Authenticate with Google and return the Calendar API client."""

        credentials: Credentials | None = None

        if self._token_path.exists():
            credentials = Credentials.from_authorized_user_file(
                self._token_path,
                self.SCOPES,
            )

        if credentials is None or not credentials.valid:
            if (
                credentials is not None
                and credentials.expired
                and credentials.refresh_token
            ):
                credentials.refresh(Request())
            else:
                if not self._credentials_path.exists():
                    raise FileNotFoundError(
                        f"Google credentials file not found: "
                        f"{self._credentials_path}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path,
                    self.SCOPES,
                )

                credentials = flow.run_local_server(
                    port=0
                )

            self._token_path.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

        return build(
            "calendar",
            "v3",
            credentials=credentials,
        )

    def get_today_events(self) -> list[dict]:
        """Return today's events from the primary calendar."""

        timezone = dt.timezone(
            dt.timedelta(hours=5, minutes=30)
        )

        now = dt.datetime.now(timezone)

        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        end = start + dt.timedelta(days=1)

        response = (
            self._service.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = []

        for event in response.get("items", []):
            event_start = event.get("start", {})

            events.append(
                {
                    "id": event.get("id"),
                    "title": event.get(
                        "summary",
                        "Untitled event",
                    ),
                    "start": event_start.get(
                        "dateTime",
                        event_start.get("date"),
                    ),
                    "description": event.get(
                        "description"
                    ),
                }
            )

        return events

    def get_events_for_date(
        self,
        target_date: dt.date,
    ) -> list[dict]:
        """Return events for a specific local calendar date."""

        timezone = dt.timezone(dt.timedelta(hours=5, minutes=30))
        start = dt.datetime.combine(target_date, dt.time.min, tzinfo=timezone)
        end = start + dt.timedelta(days=1)

        response = (
            self._service.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        events = []
        for event in response.get("items", []):
            event_start = event.get("start", {})
            events.append({
                "id": event.get("id"),
                "title": event.get("summary", "Untitled event"),
                "start": event_start.get("dateTime", event_start.get("date")),
                "description": event.get("description"),
            })
        return events

    def create_event(
        self,
        title: str,
        start: dt.datetime,
        end: dt.datetime,
        description: str | None = None,
    ) -> dict:
        """Create an event on the primary calendar."""

        if start.tzinfo is None:
            raise ValueError(
                "Calendar event start time must be timezone-aware."
            )

        if end.tzinfo is None:
            raise ValueError(
                "Calendar event end time must be timezone-aware."
            )

        if end <= start:
            raise ValueError(
                "Calendar event end time must be after start time."
            )

        event = {
            "summary": title,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "Asia/Kolkata",
            },
        }

        if description:
            event["description"] = description

        return (
            self._service.events()
            .insert(
                calendarId="primary",
                body=event,
            )
            .execute()
        )