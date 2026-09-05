from pathlib import Path

from app.services.assistant.session import SessionService


def test_session_persists_across_service_instances(
    tmp_path: Path,
) -> None:
    storage_path = tmp_path / "sessions.json"

    first_service = SessionService(storage_path)

    session = first_service.create_session()

    first_service.append_message(
        session.session_id,
        "user",
        "Explain Docker.",
    )

    first_service.append_message(
        session.session_id,
        "assistant",
        "Docker packages applications into containers.",
    )

    second_service = SessionService(storage_path)

    restored = second_service.get_session(
        session.session_id
    )

    assert restored is not None

    assert len(restored.messages) == 2

    assert restored.messages[0].role == "user"
    assert restored.messages[0].content == "Explain Docker."

    assert restored.messages[1].role == "assistant"
    assert (
        restored.messages[1].content
        == "Docker packages applications into containers."
    )


def test_session_message_order_is_preserved(
    tmp_path: Path,
) -> None:
    storage_path = tmp_path / "sessions.json"

    service = SessionService(storage_path)

    session = service.create_session()

    messages = [
        ("user", "Hello"),
        ("assistant", "Hi!"),
        ("user", "Explain Docker"),
        ("assistant", "Docker is a container platform."),
    ]

    for role, content in messages:
        service.append_message(
            session.session_id,
            role,
            content,
        )

    restored_service = SessionService(storage_path)

    restored = restored_service.get_session(
        session.session_id
    )

    assert restored is not None

    assert [
        (message.role, message.content)
        for message in restored.messages
    ] == messages


def test_unknown_session_returns_none(
    tmp_path: Path,
) -> None:
    service = SessionService(
        tmp_path / "sessions.json"
    )

    assert service.get_session(
        "does-not-exist"
    ) is None