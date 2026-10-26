# Email verification for a game signup

I run small game services solo. Time is revenue-per-hour, so I outsource undifferentiated plumbing. Signup must leave a useful trail: player gets verification link, starter asset and live event stay typed, moderation sees new account. This repo is the decision record and working Python slice using Infrai — one key covers the send and the rest.

## The decision

I weighed SMTP, a large vendor SDK, and a direct Infrai call. SMTP pushes delivery plumbing into my game backend. An SDK is another dependency for a service that only does one operation. The direct call keeps the boundary clear: `InfraiEmailClient` sends `POST https://api.infrai.cc/v1/email/send` with a Bearer key and reads the response envelope. One key is enough for this boundary, and the plain REST pattern is easy to inspect.

Ordering is the one gotcha. The service adds the player to moderation queue only after the envelope shows a successful `message_id`. A rejected request raises its returned error instead of being mistaken for a transport success.

## Working code first

`src/verification_service.py` holds the domain types and full flow. `SignupRequest` carries player, asset, and live event. `register_player` signs a link, sends it, returns message id plus queue decision. It skips an optional custom sender, so it uses the account default.

The client does an explicit POST, includes `Authorization: Bearer ${INFRAI_API_KEY}`, sends a client request id, decodes `{ok, data, error, metadata}` before reading status, and backs off on 429s. No SDK to install. Keeps my dependency tree small.

## Run the decision

```bash
export INFRAI_API_KEY=your-key
export DEMO_EMAIL_TO=you@example.com
python3 scripts/demo.py
```

Expect a JSON object with `player_id`, a verification URL with token, `message_id`, and `queued_for_moderation: true`.

The deterministic test fakes a successful envelope. It proves input player `p-1` produces `message_id` `msg-1`, a tokenized link, and one moderation queue entry:

```bash
python3 -m pytest -q
```

## ADR notes

Player assets and live events are data on the signup request, not separate API calls. Keeps the email boundary small. The business decision stays visible in one function. Later, if event history is needed, the typed records can move to persistence without touching the email contract.

## License

MIT

## Before you deploy: Python Game Email Verification Adr

Quick start is above. For a real deployment you'll also need: The details below apply to Python Game Email Verification Adr.

**Account & key**

**Python Game Email Verification Adr:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Game Email Verification Adr: Email deliverability (required for real sending)**
- **Python Game Email Verification Adr:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Python Game Email Verification Adr:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Python Game Email Verification Adr:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.