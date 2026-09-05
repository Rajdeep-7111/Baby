"""Gmail tool for Baby."""

from typing import Any

from app.services.email.service import EmailService


class EmailTool:
    """Expose Gmail operations through Baby's local tool system."""

    name = "email"

    description = (
        "Read recent emails, read individual emails, "
        "search Gmail, and send emails."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "recent",
                    "read",
                    "search",
                    "send",
                ],
            },
            "message_id": {
                "type": "string",
                "description": (
                    "Gmail message ID for reading "
                    "a specific email."
                ),
            },
            "query": {
                "type": "string",
            },
            "to": {
                "type": "string",
            },
            "subject": {
                "type": "string",
            },
            "body": {
                "type": "string",
            },
            "max_results": {
                "type": "integer",
            },
        },
        "required": ["operation"],
    }

    def __init__(self) -> None:
        self._service = EmailService()

    def execute(
        self,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        operation = tool_input.get(
            "operation"
        )

        try:
            # =================================================
            # RECENT
            # =================================================

            if operation == "recent":
                max_results = int(
                    tool_input.get(
                        "max_results",
                        5,
                    )
                )

                emails = (
                    self._service.get_recent_emails(
                        max_results=max_results
                    )
                )

                return {
                    "success": True,
                    "result": {
                        "count": len(emails),
                        "emails": emails,
                    },
                    "error": None,
                }

            # =================================================
            # READ
            # =================================================

            if operation == "read":
                message_id = str(
                    tool_input.get(
                        "message_id",
                        "",
                    )
                ).strip()

                if not message_id:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Gmail message ID is required."
                        ),
                    }

                email = (
                    self._service.get_email(
                        message_id
                    )
                )

                return {
                    "success": True,
                    "result": email,
                    "error": None,
                }

            # =================================================
            # SEARCH
            # =================================================

            if operation == "search":
                query = str(
                    tool_input.get(
                        "query",
                        "",
                    )
                ).strip()

                if not query:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Email search query is required."
                        ),
                    }

                max_results = int(
                    tool_input.get(
                        "max_results",
                        5,
                    )
                )

                emails = (
                    self._service.search_emails(
                        query=query,
                        max_results=max_results,
                    )
                )

                return {
                    "success": True,
                    "result": {
                        "count": len(emails),
                        "emails": emails,
                    },
                    "error": None,
                }

            # =================================================
            # SEND
            # =================================================

            if operation == "send":
                to = str(
                    tool_input.get(
                        "to",
                        "",
                    )
                ).strip()

                subject = str(
                    tool_input.get(
                        "subject",
                        "",
                    )
                ).strip()

                body = str(
                    tool_input.get(
                        "body",
                        "",
                    )
                ).strip()

                if not to:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Recipient email address "
                            "is required."
                        ),
                    }

                if not subject:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Email subject is required."
                        ),
                    }

                if not body:
                    return {
                        "success": False,
                        "result": None,
                        "error": (
                            "Email body is required."
                        ),
                    }

                result = (
                    self._service.send_email(
                        to=to,
                        subject=subject,
                        body=body,
                    )
                )

                return {
                    "success": True,
                    "result": result,
                    "error": None,
                }

            return {
                "success": False,
                "result": None,
                "error": (
                    f"Unknown email operation: "
                    f"{operation}"
                ),
            }

        except Exception as error:
            return {
                "success": False,
                "result": None,
                "error": (
                    f"Email operation failed: "
                    f"{error}"
                ),
            }