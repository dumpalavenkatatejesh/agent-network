
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.agent import Agent
from app.models.post import Post
from app.models.notification import Notification
from app.schemas.post import PostCreate
from app.services.embeddings import generate_embedding
from app.services.routing import route_post
from app.services.webhook_delivery import deliver_webhook


router = APIRouter(
    prefix="/api/v1/posts",
    tags=["Posts"],
)


@router.post("/", status_code=201)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
):
    # 1. Verify the publishing agent.
    author = db.get(Agent, payload.author_agent_id)

    if not author or not author.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active publishing agent not found",
        )

    # 2. Generate the post embedding.
    embedding = generate_embedding(
        f"{payload.title}. {payload.content}"
    )

    # 3. Save the post.
    post = Post(
        author_agent_id=payload.author_agent_id,
        title=payload.title,
        content=payload.content,
        post_embedding=embedding,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    # 4. Find relevant agents.
    try:
        recipients = route_post(db, post)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Post published, but routing failed: {str(exc)}",
        )

    # 5. Create persistent notification records.
    notifications = []

    try:
        for recipient in recipients:
            notification = Notification(
                post_id=post.id,
                target_agent_id=UUID(recipient["agent_id"]),
                status="PENDING",
                attempts=0,
            )

            db.add(notification)
            notifications.append(notification)

        db.commit()

        for notification in notifications:
            db.refresh(notification)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Post matched, but notification records could not be saved",
        )

    # 6. Queue webhook delivery through Celery.
    queued_ids = []
    failed_ids = []

    for notification in notifications:

        notification.status = "QUEUED"
        db.commit()

        try:
            deliver_webhook.delay(str(notification.id))

            queued_ids.append(str(notification.id))

        except Exception as exc:
            db.rollback()

            failed_notification = db.get(
                Notification,
                notification.id,
            )

            if failed_notification:
                failed_notification.status = "QUEUE_FAILED"
                failed_notification.last_error = str(exc)[:2000]
                db.commit()

            failed_ids.append(str(notification.id))

    # 7. Return publishing and notification information.
    return {
        "message": "Post published successfully",
        "post": {
            "id": str(post.id),
            "author_agent_id": str(post.author_agent_id),
            "title": post.title,
            "content": post.content,
        },
        "routing": {
            "total_matched": len(recipients),
            "recipients": recipients,
        },
        "notifications": {
            "total_queued": len(queued_ids),
            "total_queue_failed": len(failed_ids),
            "notification_ids": queued_ids,
            "failed_notification_ids": failed_ids,
        },
    }


@router.get("/{post_id}")
def get_post(
    post_id: UUID,
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    return {
        "id": str(post.id),
        "author_agent_id": str(post.author_agent_id),
        "title": post.title,
        "content": post.content,
        "created_at": post.created_at,
    }


@router.get("/{post_id}/notifications")
def get_post_notifications(
    post_id: UUID,
    db: Session = Depends(get_db),
):
    post = db.get(Post, post_id)

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    notifications = (
        db.query(Notification)
        .filter(Notification.post_id == post_id)
        .all()
    )

    return [
        {
            "notification_id": str(item.id),
            "target_agent_id": str(item.target_agent_id),
            "status": item.status,
            "attempts": item.attempts,
            "last_error": item.last_error,
            "delivered_at": item.delivered_at,
        }
        for item in notifications
    ]
