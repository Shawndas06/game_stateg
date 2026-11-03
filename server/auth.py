from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def telegram_user(init_data: str, bot_token: str, now: int | None = None) -> str:
    now = int(time.time()) if now is None else now
    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    data = dict(pairs)
    if len(data) != len(pairs): raise ValueError("Повторяющиеся поля авторизации")
    digest = data.pop("hash", "")
    # The bot-token HMAC procedure includes all received fields except hash.
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest): raise ValueError("Недействительная подпись Telegram")
    issued = int(data.get("auth_date", "0"))
    if issued > now + 30 or now - issued > 300: raise ValueError("Вход устарел. Откройте игру заново из Telegram.")
    user = json.loads(data.get("user", "{}"))
    if not isinstance(user, dict): raise ValueError("Недействительный пользователь")
    uid = user.get("id")
    if type(uid) is not int or uid <= 0: raise ValueError("Недействительный пользователь")
    return f"tg:{uid}"


def session_token(user: str, secret: str, now: int | None = None) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"user": user, "issued": int(time.time()) if now is None else now}, separators=(",", ":")).encode()).decode().rstrip("=")
    return payload + "." + hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def read_session(token: str, secret: str, now: int | None = None) -> str:
    payload, signature = token.split(".", 1)
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected): raise ValueError("Invalid session")
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    now = int(time.time()) if now is None else now
    if not 0 <= now - data["issued"] <= 86400: raise ValueError("Expired session")
    if not isinstance(data["user"], str): raise ValueError("Invalid user")
    return data["user"]
