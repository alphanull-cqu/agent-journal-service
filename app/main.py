import json
import logging
from json import JSONDecodeError
from typing import Any
from app.bootstrap_events import (
    get_repository_bootstrap_arguments,
)
from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    Request,
    status,
)

from app.config import settings
from app.github_events import summarize_github_event
from app.repository_bootstrap import install_agent_journal
from app.webhook_security import verify_github_signature


app = FastAPI(
    title="Agent Journal GitHub App Service",
    version="0.1.0",
)

logger = logging.getLogger("uvicorn.error")




def run_repository_bootstrap(
    installation_id: int,
    repository_full_name: str,
    default_branch: str,
) -> None:
    """
    在后台确保仓库已经安装最新的 Agent Journal 指令。
    """

    try:
        result = install_agent_journal(
            installation_id=installation_id,
            repository_full_name=repository_full_name,
            default_branch=default_branch,
        )

        logger.info(
            "Agent Journal bootstrap finished: "
            "repository=%s status=%s path=%s reason=%s",
            repository_full_name,
            result.get("status"),
            result.get("path"),
            result.get("reason", "none"),
        )

    except Exception:
        logger.exception(
            "Agent Journal bootstrap failed: repository=%s",
            repository_full_name,
        )





@app.get("/healthz")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/github")
async def receive_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
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
            detail=(
                "GitHub webhook payload must be "
                "a JSON object"
            ),
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

    bootstrap_arguments = (
        get_repository_bootstrap_arguments(
            event_name=event_name,
            payload=payload_data,
            github_org=settings.github_org,
        )
    )

    if event_name in {"repository", "push"}:
        if bootstrap_arguments is None:
            result["bootstrap"] = "skipped"

        else:
            (
                installation_id,
                repository_full_name,
                default_branch,
            ) = bootstrap_arguments

            background_tasks.add_task(
                run_repository_bootstrap,
                installation_id=installation_id,
                repository_full_name=(
                    repository_full_name
                ),
                default_branch=default_branch,
            )

            result["bootstrap"] = "scheduled"

    logger.info(
        "GitHub webhook received: "
        "event=%s repository=%s delivery_id=%s "
        "status=%s bootstrap=%s",
        result.get("event"),
        result.get("repository"),
        delivery_id,
        result.get("status"),
        result.get(
            "bootstrap",
            "not_applicable",
        ),
    )

    return result