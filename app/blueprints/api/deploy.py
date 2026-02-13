import hashlib
import hmac
from os import getenv

from flask import jsonify, request

from .base import bp


def _verify_signature(payload: bytes) -> bool:
    secret = getenv("DEPLOY_WEBHOOK_SECRET")
    if not secret:
        return False
    given_signature = request.headers.get("X-MobileLoTW-Signature", "")
    expected_signature = hmac.new(
        key=bytes(secret, encoding="utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(given_signature, expected_signature)


def _is_allowed_source() -> bool:
    allowed_ips_raw = getenv("DEPLOY_ALLOWED_IPS", "")
    if not allowed_ips_raw.strip():
        return True
    allowed_ips = {
        ip.strip() for ip in allowed_ips_raw.split(",") if ip.strip()
    }
    return request.remote_addr in allowed_ips


@bp.post("/api/v1/deploy")
def deploy():
    if not _is_allowed_source():
        return jsonify({"error": "source_not_allowed"}), 403

    payload = request.get_data(cache=False) or b""
    api_key_header = request.headers.get("X-API-KEY", "")
    api_key = getenv("API_KEY")
    authorized = False

    # Prefer signed webhook auth, fallback to API key header if no secret configured.
    if getenv("DEPLOY_WEBHOOK_SECRET"):
        authorized = _verify_signature(payload=payload)
    elif api_key and api_key_header:
        authorized = hmac.compare_digest(api_key_header, api_key)

    if not authorized:
        return jsonify({"error": "unauthorized"}), 401

    script_path = getenv("DEPLOY_SCRIPT_PATH")
    if not script_path:
        return jsonify({"error": "deploy_path_not_configured"}), 500

    import subprocess

    try:
        subprocess.run(
            ["/usr/bin/sudo", script_path],
            shell=False,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        return jsonify({"error": "deploy_failed", "returncode": error.returncode}), 500

    return jsonify({"status": "ok"})
