import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
import jwt

JWT_SECRET = os.getenv('JWT_SECRET', 'dev-change-me-please-use-at-least-32-bytes')
JWT_ALG = 'HS256'


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200_000)
    return f'pbkdf2_sha256$200000${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        _, rounds, salt_b64, digest_b64 = encoded.split('$', 3)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_access_token(user_id: str, minutes: int = 120) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': user_id, 'iat': now, 'exp': now + timedelta(minutes=minutes), 'type': 'access'}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    if payload.get('type') != 'access':
        raise jwt.InvalidTokenError('wrong token type')
    return str(payload['sub'])
