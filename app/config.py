import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
# print(PROJECT_ROOT)
# 从项目根目录读取 .env
load_dotenv(PROJECT_ROOT / ".env")


def get_required_env(name: str) -> str:
    """读取必需的环境变量；不存在或为空时直接报错。"""
    value = os.getenv(name)

    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value.strip()


@dataclass(frozen=True)
class Settings:
    github_app_id: int
    github_org: str
    github_private_key_path: Path
    github_webhook_secret: str


def load_settings() -> Settings:
    app_id_text = get_required_env("GITHUB_APP_ID")

    try:
        app_id = int(app_id_text)
    except ValueError as exc:
        raise RuntimeError("GITHUB_APP_ID must be an integer") from exc

    private_key_path = Path(
        get_required_env("GITHUB_PRIVATE_KEY_PATH")
    ).expanduser()

    if not private_key_path.is_absolute():
        private_key_path = PROJECT_ROOT / private_key_path

    private_key_path = private_key_path.resolve()

    if not private_key_path.is_file():
        raise RuntimeError(
            f"GitHub App private key was not found: {private_key_path}"
        )

    webhook_secret = get_required_env("GITHUB_WEBHOOK_SECRET")

    if len(webhook_secret) < 32:
        raise RuntimeError(
            "GITHUB_WEBHOOK_SECRET must contain at least 32 characters"
        )

    return Settings(
        github_app_id=app_id,
        github_org=get_required_env("GITHUB_ORG"),
        github_private_key_path=private_key_path,
        github_webhook_secret=webhook_secret,
    )


settings = load_settings()