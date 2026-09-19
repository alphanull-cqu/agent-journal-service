"""
任务能力，主动测试 像代码仓库中加入Agent.md文件，并且文件内容为AGENTS_FILE_PATH中的skill

自动化时，开启fastapi，自动监控github组织仓库的更新情况，如果有新的项目则调用该任务完成新仓库的agent文件加入

agent.md的内容需要实时修改，根据任务和使用情况更新最合适的skill规则
"""

from time import sleep
from typing import Any

from app.github_client import GitHubAPIError

from app.repository_files import (
    create_repository_file_if_missing,
    decode_repository_file_content,
    get_repository_file,
    update_repository_file,
)


AGENTS_FILE_PATH = "AGENTS.md"
AGENTS_OVERRIDE_FILE_PATH = "AGENTS.override.md"

MANAGED_BLOCK_START = "<!-- AGENT-JOURNAL:START -->"
MANAGED_BLOCK_END = "<!-- AGENT-JOURNAL:END -->"

MAX_BOOTSTRAP_ATTEMPTS = 3
RETRYABLE_GITHUB_STATUS_CODES = {409, 422}

AGENT_JOURNAL_MANAGED_BLOCK = f"""{MANAGED_BLOCK_START}

## 组织开发日志要求

本仓库启用了 Agent Journal。代码智能体必须遵守以下要求。

当本次任务对仓库中的代码、文档、配置或其他文件产生实际修改时，必须在任务结束前更新：

`.agent-journal/DEVELOPMENT_JOURNAL.md`

### 日志文件初始化

如果日志文件不存在，应创建该文件，并以以下内容开头：

    # Development Journal

    > 本文件由代码智能体持续追加，用于记录项目修改过程。

### 追加规则

- 只允许在文件末尾追加新记录。
- 不得删除、覆盖、重写或压缩历史记录。
- 如果旧记录存在错误，应追加一条更正说明。
- 每次存在实际文件修改时，应追加一条记录。
- 仅查看、分析或回答问题且没有修改文件时，不需要记录。
- 更新日志本身不需要再产生额外日志记录。
- 日志应与本次代码修改一起提交。
- 不得在日志中记录密码、Token、私钥或其他敏感信息。
- “修改过程”只记录可复现的技术步骤，不记录隐藏推理过程。

### 日志格式

每条新记录使用以下格式，并追加在文件末尾：

    ## YYYY-MM-DD HH:MM 时区 — Agent名称

    ### 任务目标

    说明本次修改要解决的问题。

    ### 修改过程

    按实际顺序概括执行的技术步骤。

    ### 修改内容

    列出修改、新增或删除的文件，以及主要变化。

    ### 遇到的问题与处理

    记录遇到的报错、原因和解决方式；没有问题时填写“无”。

    ### 验证结果

    记录执行的测试、检查命令及结果。

    ### 遗留事项

    记录尚未解决的问题或后续工作；没有时填写“无”。

{MANAGED_BLOCK_END}"""

AGENTS_FILE_CONTENT = f"""# Agent Journal 工作规范

{AGENT_JOURNAL_MANAGED_BLOCK}

"""


def merge_agent_journal_instructions(
    existing_content: str,
) -> str:
    """
    将 Agent Journal 托管区块合并到现有指令文件中。

    托管区块不存在时追加；
    托管区块已经存在时更新；
    托管区块之外的成员内容保持不变。
    """

    start_count = existing_content.count(
        MANAGED_BLOCK_START
    )
    end_count = existing_content.count(
        MANAGED_BLOCK_END
    )

    if start_count == 0 and end_count == 0:
        if not existing_content.strip():
            return AGENTS_FILE_CONTENT

        return (
            existing_content.rstrip()
            + "\n\n"
            + AGENT_JOURNAL_MANAGED_BLOCK
            + "\n"
        )

    if start_count != 1 or end_count != 1:
        raise RuntimeError(
            "Agent Journal managed block markers are malformed"
        )

    start_index = existing_content.index(
        MANAGED_BLOCK_START
    )
    end_index = existing_content.index(
        MANAGED_BLOCK_END
    )

    if end_index <= start_index:
        raise RuntimeError(
            "Agent Journal managed block markers are out of order"
        )

    end_index += len(MANAGED_BLOCK_END)

    current_managed_block = existing_content[
        start_index:end_index
    ]

    if (
        current_managed_block
        == AGENT_JOURNAL_MANAGED_BLOCK
    ):
        return existing_content

    return (
        existing_content[:start_index]
        + AGENT_JOURNAL_MANAGED_BLOCK
        + existing_content[end_index:]
    )


def get_repository_file_sha(
    file_data: dict[str, Any],
) -> str:
    """
    从 GitHub 文件响应中提取 SHA。
    """

    file_sha = file_data.get("sha")

    if not isinstance(file_sha, str):
        raise RuntimeError(
            "GitHub repository file SHA is missing"
        )

    normalized_sha = file_sha.strip()

    if not normalized_sha:
        raise RuntimeError(
            "GitHub repository file SHA is empty"
        )

    return normalized_sha


def _install_agent_journal_once(
    installation_id: int,
    repository_full_name: str,
    default_branch: str,
) -> dict[str, Any]:
    """
    向仓库安装或更新 Agent Journal 指令。

    优先处理根目录中的 AGENTS.override.md；
    否则处理 AGENTS.md。
    成员已有内容不会被删除或覆盖。
    """

    override_file = get_repository_file(
        installation_id=installation_id,
        repository_full_name=repository_full_name,
        file_path=AGENTS_OVERRIDE_FILE_PATH,
        branch=default_branch,
    )

    if override_file is not None:
        target_path = AGENTS_OVERRIDE_FILE_PATH
        existing_file = override_file

    else:
        target_path = AGENTS_FILE_PATH
        existing_file = get_repository_file(
            installation_id=installation_id,
            repository_full_name=repository_full_name,
            file_path=AGENTS_FILE_PATH,
            branch=default_branch,
        )

    if existing_file is None:
        result = create_repository_file_if_missing(
            installation_id=installation_id,
            repository_full_name=repository_full_name,
            file_path=AGENTS_FILE_PATH,
            content=AGENTS_FILE_CONTENT,
            commit_message=(
                "chore: install agent journal instructions"
            ),
            branch=default_branch,
        )

        if result is None:
            return {
                "status": "skipped",
                "path": AGENTS_FILE_PATH,
                "reason": "file was created concurrently",
            }

        return {
            "status": "created",
            "path": result["content"]["path"],
            "commit_sha": result["commit"]["sha"],
            "commit_url": result["commit"]["html_url"],
        }

    existing_content = decode_repository_file_content(
        existing_file
    )

    merged_content = merge_agent_journal_instructions(
        existing_content
    )

    if merged_content == existing_content:
        return {
            "status": "skipped",
            "path": target_path,
            "reason": "managed block already current",
        }

    result = update_repository_file(
        installation_id=installation_id,
        repository_full_name=repository_full_name,
        file_path=target_path,
        content=merged_content,
        commit_message=(
            "chore: add agent journal instructions"
        ),
        branch=default_branch,
        file_sha=get_repository_file_sha(
            existing_file
        ),
    )

    return {
        "status": "updated",
        "path": result["content"]["path"],
        "commit_sha": result["commit"]["sha"],
        "commit_url": result["commit"]["html_url"],
    }

def install_agent_journal(
    installation_id: int,
    repository_full_name: str,
    default_branch: str,
) -> dict[str, Any]:
    """
    安装或更新 Agent Journal 指令。

    如果多个 Webhook 任务同时修改同一个文件，
    遇到 GitHub 409 或 422 冲突时重新读取并重试。
    """

    for attempt in range(
        1,
        MAX_BOOTSTRAP_ATTEMPTS + 1,
    ):
        try:
            return _install_agent_journal_once(
                installation_id=installation_id,
                repository_full_name=(
                    repository_full_name
                ),
                default_branch=default_branch,
            )

        except GitHubAPIError as error:
            should_retry = (
                error.status_code
                in RETRYABLE_GITHUB_STATUS_CODES
                and attempt < MAX_BOOTSTRAP_ATTEMPTS
            )

            if not should_retry:
                raise

            sleep(0.25 * attempt)

    raise RuntimeError(
        "Agent Journal bootstrap retry loop ended unexpectedly"
    )