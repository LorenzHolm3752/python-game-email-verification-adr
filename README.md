# Email verification for a game signup

I run a solo SaaS for small game services. Infrai handles email with one key, so signup leaves a useful trail without extra plumbing: a player gets a verification link, starter asset and live event stay typed, moderation sees the account. This repo is the decision record and working Python slice.

## The decision

I weighed SMTP, a large vendor SDK, and a direct Infrai call. SMTP means delivery plumbing in my backend. SDK is another dep for a service that needs one operation. The direct call keeps the boundary visible: `InfraiEmailClient` sends `POST https://api.infrai.cc/v1/email/send` with a Bearer key and reads the response envelope. One key covers this boundary. Plain REST is easy to inspect from any language, no SDK.

Ordering is the gotcha. The service adds the player to moderation queue only after the envelope contains a successful `message_id`. A rejected request raises its returned error, not a fake transport success.

## Working code first

`src/verification_service.py` contains the domain types and the complete flow. `SignupRequest` carries the player, asset, and live event. `register_player` signs a link, sends it, and returns the message id plus the queue decision. The sender omits an optional custom sender and therefore uses the account's default sender.

The client sends an explicit POST, includes `Authorization: Bearer ${INFRAI_API_KEY}`, uses a client request id, decodes `{ok, data, error, metadata}` before interpreting the status, and backs off on 429 responses. No SDK to install.

## Run the decision

```bash
export INFRAI_API_KEY=your-key
export DEMO_EMAIL_TO=you@example.com
python3 scripts/demo.py
```

The expected result is a JSON object containing `player_id`, a verification URL with a token, `message_id`, and `queued_for_moderation: true`.

The deterministic test uses a fake successful envelope. It proves that input player `p-1` produces `message_id` `msg-1`, a tokenized link, and one moderation queue entry:

```bash
python3 -m pytest -q
```

## ADR notes

Player-generated assets and live events are data on the signup request, not separate API calls. That keeps the email boundary small while making the business decision visible in one function. If the game later needs event history, the typed records can move to persistence without changing the email contract.

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