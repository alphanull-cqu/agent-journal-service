import logging
import json
from json import JSONDecodeError
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status

from app.config import settings
from app.github_events import summarize_github_event
from app.webhook_security import verify_github_signature


app = FastAPI(
    title="Agent Journal GitHub App Service",
    version="0.1.0",
)

logger = logging.getLogger("uvicorn.error")

@app.get("/healthz")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/github")
async def receive_github_webhook(
    request: Request,
) -> dict[str, str]:
    payload = await request.body()

    signature_header = request.headers.get(
        "X-Hub-Signature-256"
    )

    signature_valid = verify_github_signature(
        payload=payload,
        signature_header=signature_header,
        webhook_secret=settings.github_webhook_secret,
    )

    if not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature",
        )

    try:
        payload_data: Any = json.loads(payload)
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from exc

    if not isinstance(payload_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub webhook payload must be a JSON object",
        )

    event_name = request.headers.get(
        "X-GitHub-Event",
        "unknown",
    )

    delivery_id = request.headers.get(
        "X-GitHub-Delivery",
        "unknown",
    )

    result = summarize_github_event(
        event_name=event_name,
        payload=payload_data,
    )

    result["delivery_id"] = delivery_id

    logger.info(
        "GitHub webhook received: "
        "event=%s repository=%s delivery_id=%s status=%s",
        result.get("event"),
        result.get("repository"),
        delivery_id,
        result.get("status"),
    )

    return result