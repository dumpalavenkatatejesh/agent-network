
import hashlib
import hmac
import json
import time

from fastapi import FastAPI, Request, HTTPException
from app.database.connection import settings

app = FastAPI(title="Asama Webhook Receiver")


@app.get("/")
def health():
    return {
        "status": "Webhook receiver running"
    }


@app.post("/webhooks/agent")
async def receive_webhook(request: Request):

    body = await request.body()

    timestamp = request.headers.get("X-Asama-Timestamp")
    signature = request.headers.get("X-Asama-Signature")

    if not timestamp or not signature:
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature headers"
        )

    # Reject old or future-dated requests.
    try:
        request_time = int(timestamp)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid timestamp"
        )

    if abs(int(time.time()) - request_time) > 300:
        raise HTTPException(
            status_code=401,
            detail="Webhook timestamp expired"
        )

    # Recalculate HMAC signature.
    signed_content = timestamp.encode() + b"." + body

    expected_signature = hmac.new(
        settings.WEBHOOK_SIGNING_SECRET.encode(),
        signed_content,
        hashlib.sha256
    ).hexdigest()

    expected_header = f"sha256={expected_signature}"

    if not hmac.compare_digest(
        expected_header,
        signature
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature"
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload"
        )

    print("\n========== WEBHOOK RECEIVED ==========")
    print(json.dumps(payload, indent=2))
    print("======================================\n")

    return {
        "success": True,
        "message": "Webhook received and signature verified",
        "event": payload.get("event")
    }
