"""Gmail integration for Baby."""

from __future__ import annotations

import base64
import re
from email.mime.text import MIMEText
from html import unescape
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build


class EmailService:
    """Provides read, search, and send access to Gmail."""

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

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _authenticate(self) -> Resource:
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
            "gmail",
            "v1",
            credentials=credentials,
        )

    # =========================================================
    # BASIC HELPERS
    # =========================================================

    @staticmethod
    def _decode_body(data: str | None) -> str:
        """Decode Gmail's URL-safe base64 body data."""

        if not data:
            return ""

        try:
            padding = "=" * (-len(data) % 4)

            return base64.urlsafe_b64decode(
                data + padding
            ).decode(
                "utf-8",
                errors="replace",
            )

        except Exception:
            return ""

    @staticmethod
    def _headers(payload: dict) -> dict[str, str]:
        """Return Gmail MIME headers as a dictionary."""

        result: dict[str, str] = {}

        for header in payload.get("headers", []) or []:
            name = header.get("name")
            value = header.get("value")

            if name and value is not None:
                result[name.lower()] = value

        return result

    # =========================================================
    # HTML → READABLE TEXT
    # =========================================================

    @staticmethod
    def _html_to_text(html: str) -> str:
        """
        Convert HTML email content into readable plain text.

        This prevents raw HTML, Outlook conditional comments,
        tracking markup, scripts, and styles from reaching
        the frontend.
        """

        if not html:
            return ""

        # -----------------------------------------------------
        # Remove Outlook / Microsoft conditional comments.
        # -----------------------------------------------------

        html = re.sub(
            r"<!--\s*\[if.*?<!\s*\[endif\]\s*-->",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # Remove any remaining HTML comments.
        html = re.sub(
            r"<!--.*?-->",
            "",
            html,
            flags=re.DOTALL,
        )

        # -----------------------------------------------------
        # Remove non-visible elements.
        # -----------------------------------------------------

        html = re.sub(
            r"<(script|style|head|noscript).*?>.*?</\1>",
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # -----------------------------------------------------
        # Preserve useful line breaks.
        # -----------------------------------------------------

        html = re.sub(
            r"<\s*br\s*/?\s*>",
            "\n",
            html,
            flags=re.IGNORECASE,
        )

        html = re.sub(
            r"<\s*/\s*(p|div|tr|h[1-6])\s*>",
            "\n",
            html,
            flags=re.IGNORECASE,
        )

        # -----------------------------------------------------
        # Convert list items.
        # -----------------------------------------------------

        html = re.sub(
            r"<\s*li[^>]*>",
            "• ",
            html,
            flags=re.IGNORECASE,
        )

        html = re.sub(
            r"<\s*/\s*li\s*>",
            "\n",
            html,
            flags=re.IGNORECASE,
        )

        # -----------------------------------------------------
        # Remove all remaining HTML tags.
        # -----------------------------------------------------

        html = re.sub(
            r"<[^>]+>",
            "",
            html,
        )

        # -----------------------------------------------------
        # Decode entities.
        # -----------------------------------------------------

        text = unescape(html)

        # Non-breaking spaces → normal spaces.
        text = text.replace("\xa0", " ")

        # Normalize carriage returns.
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Remove trailing whitespace from lines.
        text = re.sub(
            r"[ \t]+\n",
            "\n",
            text,
        )

        # Remove excessive indentation.
        text = re.sub(
            r"\n[ \t]+",
            "\n",
            text,
        )

        # More than two blank lines → two.
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text.strip()

    # =========================================================
    # MIME BODY EXTRACTION
    # =========================================================

    def _extract_body(self, payload: dict) -> str:
        """
        Extract the most readable body from a Gmail MIME payload.

        Priority:
            1. text/plain
            2. text/html converted to readable text
        """

        plain_parts: list[str] = []
        html_parts: list[str] = []

        def walk(part: dict) -> None:
            mime_type = part.get(
                "mimeType",
                "",
            )

            body = part.get(
                "body",
                {},
            ) or {}

            data = body.get("data")

            if data:
                decoded = self._decode_body(data)

                if mime_type == "text/plain":
                    if decoded.strip():
                        plain_parts.append(
                            decoded.strip()
                        )

                elif mime_type == "text/html":
                    if decoded.strip():
                        html_parts.append(
                            decoded.strip()
                        )

            for child in (
                part.get("parts", [])
                or []
            ):
                walk(child)

        walk(payload)

        # -----------------------------------------------------
        # Prefer plain text whenever available.
        # -----------------------------------------------------

        if plain_parts:
            return "\n\n".join(
                part
                for part in plain_parts
                if part.strip()
            ).strip()

        # -----------------------------------------------------
        # Fall back to cleaned HTML.
        # -----------------------------------------------------

        if html_parts:
            return self._html_to_text(
                "\n\n".join(html_parts)
            )

        return ""

    # =========================================================
    # RECENT EMAILS
    # =========================================================

    def get_recent_emails(
        self,
        max_results: int = 5,
    ) -> list[dict]:
        """Return recent inbox messages."""

        response = (
            self._service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=max_results,
            )
            .execute()
        )

        messages = response.get(
            "messages",
            [],
        )

        emails: list[dict] = []

        for message in messages:
            message_id = message.get("id")

            if not message_id:
                continue

            detail = (
                self._service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=[
                        "From",
                        "To",
                        "Subject",
                        "Date",
                    ],
                )
                .execute()
            )

            payload = detail.get(
                "payload",
                {},
            )

            headers = self._headers(
                payload
            )

            emails.append(
                {
                    "id": detail.get("id"),
                    "thread_id": detail.get(
                        "threadId"
                    ),
                    "from": headers.get(
                        "from",
                        "",
                    ),
                    "to": headers.get(
                        "to",
                        "",
                    ),
                    "subject": headers.get(
                        "subject",
                        "",
                    ),
                    "date": headers.get(
                        "date",
                        "",
                    ),
                    "snippet": detail.get(
                        "snippet",
                        "",
                    ),
                }
            )

        return emails

    # =========================================================
    # SEARCH EMAILS
    # =========================================================

    def search_emails(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict]:
        """Search Gmail using Gmail's search syntax."""

        response = (
            self._service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=max_results,
            )
            .execute()
        )

        messages = response.get(
            "messages",
            [],
        )

        emails: list[dict] = []

        for message in messages:
            message_id = message.get("id")

            if not message_id:
                continue

            detail = (
                self._service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=[
                        "From",
                        "To",
                        "Subject",
                        "Date",
                    ],
                )
                .execute()
            )

            payload = detail.get(
                "payload",
                {},
            )

            headers = self._headers(
                payload
            )

            emails.append(
                {
                    "id": detail.get("id"),
                    "thread_id": detail.get(
                        "threadId"
                    ),
                    "from": headers.get(
                        "from",
                        "",
                    ),
                    "to": headers.get(
                        "to",
                        "",
                    ),
                    "subject": headers.get(
                        "subject",
                        "",
                    ),
                    "date": headers.get(
                        "date",
                        "",
                    ),
                    "snippet": detail.get(
                        "snippet",
                        "",
                    ),
                }
            )

        return emails

    # =========================================================
    # READ ONE EMAIL
    # =========================================================

    def get_email(
        self,
        message_id: str,
    ) -> dict:
        """Return a complete readable Gmail message."""

        detail = (
            self._service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

        payload = detail.get(
            "payload",
            {},
        )

        headers = self._headers(
            payload
        )

        body = self._extract_body(
            payload
        )

        return {
            "id": detail.get("id"),
            "thread_id": detail.get(
                "threadId"
            ),
            "from": headers.get(
                "from",
                "",
            ),
            "to": headers.get(
                "to",
                "",
            ),
            "cc": headers.get(
                "cc",
                "",
            ),
            "bcc": headers.get(
                "bcc",
                "",
            ),
            "subject": headers.get(
                "subject",
                "",
            ),
            "date": headers.get(
                "date",
                "",
            ),
            "body": body,
            "snippet": detail.get(
                "snippet",
                "",
            ),
            "label_ids": detail.get(
                "labelIds",
                [],
            ),
        }

    # =========================================================
    # SEND EMAIL
    # =========================================================

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> dict:
        """Send a plain-text email through Gmail."""

        message = MIMEText(
            body,
            "plain",
            "utf-8",
        )

        message["to"] = to
        message["subject"] = subject

        encoded_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        result = (
            self._service.users()
            .messages()
            .send(
                userId="me",
                body={
                    "raw": encoded_message
                },
            )
            .execute()
        )

        return {
            "id": result.get("id"),
            "thread_id": result.get(
                "threadId"
            ),
        }