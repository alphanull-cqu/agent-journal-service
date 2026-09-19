import base64
import unittest
from unittest.mock import patch

from app.github_client import GitHubAPIError
from app.repository_bootstrap import (
    AGENTS_FILE_CONTENT,
    MANAGED_BLOCK_END,
    MANAGED_BLOCK_START,
    install_agent_journal,
    merge_agent_journal_instructions,
)


class AgentJournalMergeTests(unittest.TestCase):
    def test_preserves_member_content_and_is_idempotent(
        self,
    ) -> None:
        member_content = """# 成员项目规范

- 使用 pytest 运行测试。
- 修改接口后更新文档。
"""

        first_merge = merge_agent_journal_instructions(
            member_content
        )
        second_merge = merge_agent_journal_instructions(
            first_merge
        )

        self.assertIn(
            "- 使用 pytest 运行测试。",
            first_merge,
        )
        self.assertEqual(
            1,
            first_merge.count(MANAGED_BLOCK_START),
        )
        self.assertEqual(
            first_merge,
            second_merge,
        )

    def test_updates_existing_managed_block(
        self,
    ) -> None:
        existing_content = (
            "# 成员项目规范\n\n"
            f"{MANAGED_BLOCK_START}\n"
            "旧版开发日志要求\n"
            f"{MANAGED_BLOCK_END}\n"
        )

        merged_content = (
            merge_agent_journal_instructions(
                existing_content
            )
        )

        self.assertIn(
            "# 成员项目规范",
            merged_content,
        )
        self.assertNotIn(
            "旧版开发日志要求",
            merged_content,
        )
        self.assertIn(
            ".agent-journal/DEVELOPMENT_JOURNAL.md",
            merged_content,
        )
        self.assertEqual(
            1,
            merged_content.count(
                MANAGED_BLOCK_START
            ),
        )

    def test_rejects_malformed_markers(
        self,
    ) -> None:
        malformed_content = (
            "# 成员项目规范\n\n"
            f"{MANAGED_BLOCK_START}\n"
            "缺少结束标记\n"
        )

        with self.assertRaises(RuntimeError):
            merge_agent_journal_instructions(
                malformed_content
            )


class AgentJournalInstallTests(unittest.TestCase):
    def test_updates_existing_agents_file(
        self,
    ) -> None:
        member_content = """# 成员项目规范

- 保留成员自己的要求。
"""

        existing_file = {
            "sha": "member-file-sha",
            "encoding": "base64",
            "content": base64.b64encode(
                member_content.encode("utf-8")
            ).decode("ascii"),
        }

        update_response = {
            "content": {
                "path": "AGENTS.md",
            },
            "commit": {
                "sha": "test-commit-sha",
                "html_url": (
                    "https://example.test/commit/test"
                ),
            },
        }

        with (
            patch(
                "app.repository_bootstrap."
                "get_repository_file",
                side_effect=[None, existing_file],
            ),
            patch(
                "app.repository_bootstrap."
                "update_repository_file",
                return_value=update_response,
            ) as update_mock,
            patch(
                "app.repository_bootstrap."
                "create_repository_file_if_missing",
            ) as create_mock,
        ):
            result = install_agent_journal(
                installation_id=123,
                repository_full_name=(
                    "alphanull-cqu/example"
                ),
                default_branch="main",
            )

        updated_content = (
            update_mock.call_args.kwargs["content"]
        )

        self.assertEqual(
            "updated",
            result["status"],
        )
        self.assertIn(
            "- 保留成员自己的要求。",
            updated_content,
        )
        self.assertEqual(
            "member-file-sha",
            update_mock.call_args.kwargs[
                "file_sha"
            ],
        )
        create_mock.assert_not_called()

    def test_skips_current_managed_block(
        self,
    ) -> None:
        existing_file = {
            "sha": "current-file-sha",
            "encoding": "base64",
            "content": base64.b64encode(
                AGENTS_FILE_CONTENT.encode("utf-8")
            ).decode("ascii"),
        }

        with (
            patch(
                "app.repository_bootstrap."
                "get_repository_file",
                side_effect=[None, existing_file],
            ),
            patch(
                "app.repository_bootstrap."
                "update_repository_file",
            ) as update_mock,
            patch(
                "app.repository_bootstrap."
                "create_repository_file_if_missing",
            ) as create_mock,
        ):
            result = install_agent_journal(
                installation_id=123,
                repository_full_name=(
                    "alphanull-cqu/example"
                ),
                default_branch="main",
            )

        self.assertEqual(
            "skipped",
            result["status"],
        )
        update_mock.assert_not_called()
        create_mock.assert_not_called()

    def test_retries_concurrent_update_conflict(
        self,
    ) -> None:
        with (
            patch(
                "app.repository_bootstrap."
                "_install_agent_journal_once",
                side_effect=[
                    GitHubAPIError(
                        status_code=409,
                        message="simulated conflict",
                    ),
                    {
                        "status": "skipped",
                        "path": "AGENTS.md",
                        "reason": (
                            "managed block already current"
                        ),
                    },
                ],
            ) as install_once_mock,
            patch(
                "app.repository_bootstrap.sleep",
            ) as sleep_mock,
        ):
            result = install_agent_journal(
                installation_id=123,
                repository_full_name=(
                    "alphanull-cqu/example"
                ),
                default_branch="main",
            )

        self.assertEqual(
            "skipped",
            result["status"],
        )
        self.assertEqual(
            2,
            install_once_mock.call_count,
        )
        sleep_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()