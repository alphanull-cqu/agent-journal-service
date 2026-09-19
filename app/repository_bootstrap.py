"""
任务能力，主动测试 像代码仓库中加入Agent.md文件，并且文件内容为AGENTS_FILE_PATH中的skill

自动化时，开启fastapi，自动监控github组织仓库的更新情况，如果有新的项目则调用该任务完成新仓库的agent文件加入

agent.md的内容需要实时修改，根据任务和使用情况更新最合适的skill规则
"""

from typing import Any

from app.repository_files import (
    create_repository_file_if_missing,
)


AGENTS_FILE_PATH = "AGENTS.md"

AGENTS_FILE_CONTENT = """# Agent Journal 工作规范

本仓库启用了 Agent Journal。代码智能体应遵守以下要求。

## 开发日志要求

当本次任务对仓库中的代码、文档、配置或其他文件产生实际修改时，必须在任务结束前更新：

`.agent-journal/DEVELOPMENT_JOURNAL.md`

## 日志文件初始化

如果日志文件不存在，应创建该文件，并以以下内容开头：

    # Development Journal

    > 本文件由代码智能体持续追加，用于记录项目修改过程。

## 追加规则

- 只允许在文件末尾追加新记录。
- 不得删除、覆盖、重写或压缩历史记录。
- 如果旧记录存在错误，应追加一条更正说明。
- 每次存在实际文件修改时，应追加一条记录。
- 仅查看、分析或回答问题且没有修改文件时，不需要记录。
- 更新日志本身不需要再产生额外日志记录。
- 日志应与本次代码修改一起提交。
- 不得在日志中记录密码、Token、私钥或其他敏感信息。
- “修改过程”只记录可复现的技术步骤，不记录隐藏推理过程。

## 日志格式

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
"""


def install_agent_journal(
    installation_id: int,
    repository_full_name: str,
    default_branch: str,
) -> dict[str, Any]:
    """
    向仓库安装 Agent Journal 指令文件。

    已有 AGENTS.md 时不会覆盖。
    """

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
            "reason": "file already exists",
        }

    return {
        "status": "created",
        "path": result["content"]["path"],
        "commit_sha": result["commit"]["sha"],
        "commit_url": result["commit"]["html_url"],
    }