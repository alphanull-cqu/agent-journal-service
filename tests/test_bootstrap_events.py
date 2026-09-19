import unittest
from copy import deepcopy

from app.bootstrap_events import (
    get_repository_bootstrap_arguments,
)


class BootstrapEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.github_org = "alphanull-cqu"

        self.push_payload = {
            "repository": {
                "full_name": (
                    "alphanull-cqu/example-project"
                ),
                "default_branch": "main",
                "owner": {
                    "login": "alphanull-cqu",
                },
            },
            "installation": {
                "id": 162746508,
            },
            "ref": "refs/heads/main",
            "after": "abc123",
            "deleted": False,
        }

    def test_default_branch_push_is_accepted(
        self,
    ) -> None:
        result = get_repository_bootstrap_arguments(
            event_name="push",
            payload=self.push_payload,
            github_org=self.github_org,
        )

        self.assertEqual(
            (
                162746508,
                "alphanull-cqu/example-project",
                "main",
            ),
            result,
        )

    def test_feature_branch_push_is_skipped(
        self,
    ) -> None:
        payload = deepcopy(self.push_payload)
        payload["ref"] = "refs/heads/feature/test"

        result = get_repository_bootstrap_arguments(
            event_name="push",
            payload=payload,
            github_org=self.github_org,
        )

        self.assertIsNone(result)

    def test_deleted_branch_push_is_skipped(
        self,
    ) -> None:
        payload = deepcopy(self.push_payload)
        payload["deleted"] = True
        payload["after"] = "0" * 40

        result = get_repository_bootstrap_arguments(
            event_name="push",
            payload=payload,
            github_org=self.github_org,
        )

        self.assertIsNone(result)

    def test_repository_created_is_accepted(
        self,
    ) -> None:
        payload = {
            "action": "created",
            "repository": (
                self.push_payload["repository"]
            ),
            "installation": (
                self.push_payload["installation"]
            ),
        }

        result = get_repository_bootstrap_arguments(
            event_name="repository",
            payload=payload,
            github_org=self.github_org,
        )

        self.assertEqual(
            (
                162746508,
                "alphanull-cqu/example-project",
                "main",
            ),
            result,
        )

    def test_other_repository_action_is_skipped(
        self,
    ) -> None:
        payload = {
            "action": "edited",
            "repository": (
                self.push_payload["repository"]
            ),
            "installation": (
                self.push_payload["installation"]
            ),
        }

        result = get_repository_bootstrap_arguments(
            event_name="repository",
            payload=payload,
            github_org=self.github_org,
        )

        self.assertIsNone(result)

    def test_foreign_organization_is_skipped(
        self,
    ) -> None:
        payload = deepcopy(self.push_payload)
        payload["repository"]["full_name"] = (
            "other-org/example-project"
        )
        payload["repository"]["owner"]["login"] = (
            "other-org"
        )

        result = get_repository_bootstrap_arguments(
            event_name="push",
            payload=payload,
            github_org=self.github_org,
        )

        self.assertIsNone(result)

    def test_unrelated_event_is_skipped(
        self,
    ) -> None:
        result = get_repository_bootstrap_arguments(
            event_name="pull_request",
            payload=self.push_payload,
            github_org=self.github_org,
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()