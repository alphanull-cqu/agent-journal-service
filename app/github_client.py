import json
import urllib.error
import urllib.request
from typing import Any

from app.github_auth import (
    GITHUB_API_BASE_URL,
    GITHUB_API_VERSION,
    GITHUB_USER_AGENT,
    create_installation_access_token,
)


class GitHubAPIError(RuntimeError):
    """GitHub API 请求失败。"""

    def __init__(
        self,
        status_code: int,
        message: str,
    ) -> None:
        self.status_code = status_code
        self.message = message

        super().__init__(
            f"GitHub API request failed "
            f"with status {status_code}: {message}"
        )


def github_api_request(
    installation_id: int,
    method: str,
    endpoint: str,
    body: dict[str, Any] | None = None,
) -> Any:
    """
    使用 GitHub App Installation Token 调用 GitHub API。

    endpoint 示例：
        /repos/alphanull-cqu/agent-journal-test
    """

    if not endpoint.startswith("/"):
        raise ValueError(
            "GitHub API endpoint must start with '/'"
        )

    access_token = create_installation_access_token(
        installation_id
    )

    request_body = None

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": GITHUB_USER_AGENT,
    }

    if body is not None:
        request_body = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=f"{GITHUB_API_BASE_URL}{endpoint}",
        data=request_body,
        method=method.upper(),
        headers=headers,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            if response.status == 204:
                return None

            return json.load(response)

    except urllib.error.HTTPError as error:
        error_text = error.read().decode(
            "utf-8",
            errors="replace",
        )

        try:
            error_data = json.loads(error_text)
            error_message = error_data.get(
                "message",
                error_text,
            )
        except json.JSONDecodeError:
            error_message = error_text or str(error.reason)

        raise GitHubAPIError(
            status_code=error.code,
            message=error_message,
        ) from error