import hashlib
import hmac


SIGNATURE_PREFIX = "sha256="


def verify_github_signature(
    payload: bytes,
    signature_header: str | None,
    webhook_secret: str,
) -> bool:
    """
    验证请求是否由 GitHub 使用正确的 Webhook Secret 签名。

    payload 必须是未经解析和修改的原始请求体。
    """

    if not signature_header:
        return False

    if not signature_header.startswith(SIGNATURE_PREFIX):
        return False

    expected_signature = SIGNATURE_PREFIX + hmac.new(
        key=webhook_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature_header,
    )