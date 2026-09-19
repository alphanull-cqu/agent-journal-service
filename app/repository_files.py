import base64
from typing import Any
from urllib.parse import quote

from app.github_client import (
    GitHubAPIError,
    github_api_request,
)


def get_repository_file(
    installation_id: int,
    repository_full_name: str,
    file_path: str,
    branch: str,
) -> dict[str, Any] | None:
    """
    读取仓库文件。

    文件不存在时返回 None，不存在之外的错误继续抛出。
    """

    normalized_path = file_path.strip("/")

    if not normalized_path:
        raise ValueError("Repository file path cannot be empty")

    encoded_path = quote(
        normalized_path,
        safe="/",
    )
    encoded_branch = quote(
        branch,
        safe="",
    )

    endpoint = (
        f"/repos/{repository_full_name}/contents/"
        f"{encoded_path}?ref={encoded_branch}"
    )

    try:
        result = github_api_request(
            installation_id=installation_id,
            method="GET",
            endpoint=endpoint,
        )

    except GitHubAPIError as error:
        if error.status_code == 404:
            return None

        raise

    if not isinstance(result, dict):
        raise RuntimeError(
            "GitHub returned an unexpected file response"
        )

    return result


def create_repository_file_if_missing(
    installation_id: int,
    repository_full_name: str,
    file_path: str,
    content: str,
    commit_message: str,
    branch: str,
) -> dict[str, Any] | None:
    """
    文件不存在时创建文件。

    创建成功时返回 GitHub API 响应；
    文件已经存在时返回 None，不覆盖原文件。
    """

    existing_file = get_repository_file(
        installation_id=installation_id,
        repository_full_name=repository_full_name,
        file_path=file_path,
        branch=branch,
    )

    if existing_file is not None:
        return None

    normalized_path = file_path.strip("/")
    encoded_path = quote(
        normalized_path,
        safe="/",
    )

    encoded_content = base64.b64encode(
        content.encode("utf-8")
    ).decode("ascii")

    result = github_api_request(
        installation_id=installation_id,
        method="PUT",
        endpoint=(
            f"/repos/{repository_full_name}/contents/"
            f"{encoded_path}"
        ),
        body={
            "message": commit_message,
            "content": encoded_content,
            "branch": branch,
        },
    )

    if not isinstance(result, dict):
        raise RuntimeError(
            "GitHub returned an unexpected create-file response"
        )

    return result