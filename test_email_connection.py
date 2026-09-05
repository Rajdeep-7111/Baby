from app.services.email.service import EmailService


email = EmailService()

messages = email.get_recent_emails(5)

print(f"Found {len(messages)} recent emails.")

for message in messages:
    print("-" * 60)
    print("From:", message["from"])
    print("Subject:", message["subject"])
    print("Date:", message["date"])
    print("Snippet:", message["snippet"])