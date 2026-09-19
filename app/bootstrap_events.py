from typing import Any


ZERO_COMMIT_SHA = "0" * 40


def get_repository_bootstrap_arguments(
    event_name: str,
    payload: dict[str, Any],
    github_org: str,
) -> tuple[int, str, str] | None:
    """
    从 Repository 或 Push 事件中提取初始化参数。

    只有指定组织内的新仓库事件或默认分支 Push
    才允许触发初始化。
    """

    if event_name not in {"repository", "push"}:
        return None

    repository = payload.get("repository")
    installation = payload.get("installation")

    if not isinstance(repository, dict):
        return None

    if not isinstance(installation, dict):
        return None

    repository_full_name = repository.get(
        "full_name"
    )
    installation_id = installation.get("id")
    default_branch = repository.get(
        "default_branch"
    )

    owner = repository.get("owner")
    owner_login = (
        owner.get("login")
        if isinstance(owner, dict)
        else None
    )

    if (
        not isinstance(repository_full_name, str)
        or not repository_full_name
        or not isinstance(installation_id, int)
        or not isinstance(owner_login, str)
        or owner_login.casefold()
        != github_org.casefold()
    ):
        return None

    if (
        not isinstance(default_branch, str)
        or not default_branch
    ):
        default_branch = "main"

    if event_name == "repository":
        if payload.get("action") != "created":
            return None

    if event_name == "push":
        pushed_ref = payload.get("ref")
        after_sha = payload.get("after")

        if payload.get("deleted") is True:
            return None

        if (
            not isinstance(pushed_ref, str)
            or pushed_ref
            != f"refs/heads/{default_branch}"
        ):
            return None

        if (
            not isinstance(after_sha, str)
            or not after_sha
            or after_sha == ZERO_COMMIT_SHA
        ):
            return None

    return (
        installation_id,
        repository_full_name,
        default_branch,
    )