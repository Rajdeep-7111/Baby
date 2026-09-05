from datetime import datetime, timedelta

from app.services.calendar.service import CalendarService


calendar = CalendarService()

start = datetime.now().astimezone() + timedelta(hours=1)
end = start + timedelta(minutes=30)

event = calendar.create_event(
    title="Baby Calendar Test",
    start=start,
    end=end,
    description="Test event created by Baby AI Assistant.",
)

print("Event created successfully!")
print("Event ID:", event.get("id"))
print("Event link:", event.get("htmlLink"))