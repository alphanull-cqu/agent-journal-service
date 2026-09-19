import json
import time
import urllib.request

import jwt

from app.config import settings


GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"
GITHUB_USER_AGENT = "agent-journal-service"

JWT_CLOCK_SKEW_SECONDS = 60
JWT_LIFETIME_SECONDS = 9 * 60


def generate_github_app_jwt() -> str:
    """
    生成用于 GitHub App 身份认证的短期 JWT。

    JWT 只在内存中生成，不写入文件，也不记录到日志。
    """

    current_time = int(time.time())

    payload = {
        "iat": current_time - JWT_CLOCK_SKEW_SECONDS,
        "exp": current_time + JWT_LIFETIME_SECONDS,
        "iss": str(settings.github_app_id),
    }

    private_key = settings.github_private_key_path.read_bytes()

    encoded_jwt = jwt.encode(
        payload=payload,
        key=private_key,
        algorithm="RS256",
    )

    return encoded_jwt


def create_installation_access_token(
    installation_id: int,
) -> str:
    """
    为指定的 GitHub App Installation 获取访问令牌。

    返回的令牌只保存在内存中，不写入文件，也不输出到日志。
    """

    if installation_id <= 0:
        raise ValueError(
            "GitHub installation_id must be a positive integer"
        )

    app_jwt = generate_github_app_jwt()

    request = urllib.request.Request(
        url=(
            f"{GITHUB_API_BASE_URL}/app/installations/"
            f"{installation_id}/access_tokens"
        ),
        data=b"{}",
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {app_jwt}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": GITHUB_USER_AGENT,
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30, 
    ) as response:
        response_data = json.load(response)

    access_token = response_data.get("token")

    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError(
            "GitHub did not return an installation access token"
        )

    return access_token