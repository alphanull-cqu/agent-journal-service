from typing import Any


def get_text(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default

    return str(value)


def get_repository_name(payload: dict[str, Any]) -> str:
    repository = payload.get("repository")

    if not isinstance(repository, dict):
        return "unknown"

    return get_text(repository.get("full_name"))


def summarize_github_event(
    event_name: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    """
    提取不同 GitHub 事件中的关键字段。

    当前只做事件识别和信息提取，不执行仓库写入操作。
    """

    result = {
        "status": "accepted",
        "event": event_name,
        "repository": get_repository_name(payload),
    }

    if event_name == "ping":
        result["message"] = "pong"
        return result

    if event_name == "repository":
        result["action"] = get_text(payload.get("action"))
        return result

    if event_name == "push":
        result["ref"] = get_text(payload.get("ref"))
        result["after"] = get_text(payload.get("after"))
        return result

    if event_name == "pull_request":
        result["action"] = get_text(payload.get("action"))
        result["pull_request_number"] = get_text(
            payload.get("number")
        )
        return result

    result["status"] = "ignored"
    return result