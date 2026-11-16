
import hashlib
import hmac
import json
import time

from datetime import datetime, timezone

import httpx
from celery import shared_task

from app.database.connection import settings, SessionLocal
from app.models.notification import Notification
from app.models.post import Post
from app.models.agent import Agent


@shared_task(
    bind=True,
    name="deliver_webhook",
    max_retries=3,
)
def deliver_webhook(self, notification_id: str):

    db = SessionLocal()

    try:
        notification = db.get(Notification, notification_id)

        if notification is None:
            return {"status": "NOT_FOUND"}

        if notification.status == "DELIVERED":
            return {"status": "DELIVERED"}

        post = db.get(Post, notification.post_id)
        agent = db.get(Agent, notification.target_agent_id)

        if post is None or agent is None:
            notification.status = "FAILED"
            notification.last_error = "Post or agent not found"
            db.commit()
            return {"status": "FAILED"}

        notification.attempts += 1
        notification.status = "SENDING"
        db.commit()

        payload = {
            "event": "post.created",
            "notification_id": str(notification.id),
            "post": {
                "id": str(post.id),
                "title": post.title,
                "content": post.content,
                "author_agent_id": str(post.author_agent_id),
            },
            "recipient": {
                "agent_id": str(agent.id),
                "company_name": agent.company_name,
            },
        }

        body = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        timestamp = str(int(time.time()))

        signed_content = timestamp.encode() + b"." + body

        signature = hmac.new(
            settings.WEBHOOK_SIGNING_SECRET.encode("utf-8"),
            signed_content,
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Asama-Timestamp": timestamp,
            "X-Asama-Signature": f"sha256={signature}",
            "X-Asama-Event": "post.created",
        }

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                agent.webhook_url,
                content=body,
                headers=headers,
            )
            response.raise_for_status()

        notification.status = "DELIVERED"
        notification.last_error = None
        notification.delivered_at = datetime.now(timezone.utc)

        db.commit()

        return {
            "status": "DELIVERED",
            "notification_id": notification_id,
            "http_status": response.status_code,
        }

    except Exception as exc:
        db.rollback()

        notification = db.get(Notification, notification_id)

        if notification is not None:
            notification.last_error = str(exc)[:2000]

            if self.request.retries < self.max_retries:
                notification.status = "RETRYING"
            else:
                notification.status = "FAILED"

            db.commit()

        if self.request.retries < self.max_retries:
            raise self.retry(
                exc=exc,
                countdown=2 ** (self.request.retries + 1),
            )

        return {
            "status": "FAILED",
            "notification_id": notification_id,
            "error": str(exc)[:500],
        }

    finally:
        db.close()
