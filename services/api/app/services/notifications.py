from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Notification, User


class NotificationService:
    def create_action_notification(
        self,
        db: Session,
        user: User,
        title: str,
        body: str,
        payload: dict,
    ) -> Notification:
        notification = Notification(
            user_id=user.id,
            channel="in_app",
            title=title,
            body=body,
            status="sent",
            payload=payload,
            sent_at=datetime.now(UTC),
        )
        db.add(notification)
        return notification
