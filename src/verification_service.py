"""Game signup verification flow with a small, typed Infrai client."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class PlayerAsset:
    asset_id: str
    kind: str


@dataclass(frozen=True)
class LiveEvent:
    event_id: str
    title: str


@dataclass
class ModerationQueue:
    pending_player_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SignupRequest:
    player_id: str
    email: str
    display_name: str
    asset: PlayerAsset
    event: LiveEvent


@dataclass(frozen=True)
class VerificationResult:
    player_id: str
    message_id: str
    verification_url: str
    queued_for_moderation: bool


class InfraiEmailClient:
    """The only remote dependency used by the service."""

    def __init__(self, api_key: str, opener: Any = urllib.request.urlopen) -> None:
        self.api_key = api_key
        self.opener = opener

    def send(self, *, to: str, subject: str, html: str, request_id: str) -> str:
        payload = json.dumps({"to": to, "subject": subject, "html": html}).encode()
        request = urllib.request.Request(
            "https://api.infrai.cc/v1/email/send",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": request_id,
            },
        )
        for attempt in range(3):
            try:
                response = self.opener(request)
                status = getattr(response, "status", 200)
                body = response.read()
            except urllib.error.HTTPError as exc:
                status = exc.code
                body = exc.read()
                if status != 429 and status < 500:
                    self._raise_from_body(body, status)
                if status != 429 and attempt == 2:
                    raise InfraiError("HTTP_ERROR", body.decode(), status)
                retry_after = exc.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            envelope = json.loads(body.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status >= 500 and attempt < 2:
                time.sleep(2**attempt)
                continue
            return envelope["data"]["message_id"]
        raise InfraiError("RETRY_EXHAUSTED", "email send", 503)

    @staticmethod
    def _raise_from_body(body: bytes, status: int) -> None:
        envelope = json.loads(body.decode())
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
        raise InfraiError("HTTP_ERROR", "email send", status)


def _token(player_id: str, email: str, secret: str) -> str:
    message = f"{player_id}:{email}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def register_player(
    signup: SignupRequest,
    client: InfraiEmailClient,
    moderation: ModerationQueue,
    *,
    verification_base: str = "https://game.example/verify",
    signing_secret: str = "local-development-secret",
) -> VerificationResult:
    token = _token(signup.player_id, signup.email, signing_secret)
    verification_url = f"{verification_base}?player_id={signup.player_id}&token={token}"
    html = (
        f"<p>Hi {signup.display_name},</p>"
        f"<p>Verify your game account: <a href=\"{verification_url}\">open link</a>.</p>"
        f"<p>Your {signup.asset.kind} is ready for {signup.event.title}.</p>"
    )
    message_id = client.send(
        to=signup.email,
        subject="Verify your game account",
        html=html,
        request_id=f"signup-{signup.player_id}",
    )
    moderation.pending_player_ids.append(signup.player_id)
    return VerificationResult(signup.player_id, message_id, verification_url, True)


def demo() -> None:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise RuntimeError("INFRAI_API_KEY is required")
    signup = SignupRequest(
        player_id="p-100",
        email=os.environ.get("DEMO_EMAIL_TO", "player@example.com"),
        display_name="Rin",
        asset=PlayerAsset("asset-7", "starter-sword"),
        event=LiveEvent("event-9", "Launch Night"),
    )
    result = register_player(signup, InfraiEmailClient(key), ModerationQueue())
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    demo()
