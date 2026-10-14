import json

from src.verification_service import (
    InfraiEmailClient,
    LiveEvent,
    ModerationQueue,
    PlayerAsset,
    SignupRequest,
    register_player,
)


class FakeResponse:
    status = 200

    def read(self):
        return json.dumps({"ok": True, "data": {"message_id": "msg-1"}}).encode()


def test_signup_sends_link_and_queues_player():
    requests = []

    def opener(request):
        requests.append(request)
        return FakeResponse()

    queue = ModerationQueue()
    signup = SignupRequest(
        "p-1", "rin@example.com", "Rin", PlayerAsset("a-1", "badge"), LiveEvent("e-1", "Finals")
    )
    result = register_player(signup, InfraiEmailClient("test-key", opener), queue)
    payload = json.loads(requests[0].data)
    assert result.message_id == "msg-1"
    assert "token=" in result.verification_url
    assert payload["to"] == "rin@example.com"
    assert payload["subject"] == "Verify your game account"
    assert queue.pending_player_ids == ["p-1"]
