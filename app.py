import json
import os

import httpx
from fastapi import FastAPI, HTTPException, Request
from erlc_api.webhooks import assert_valid_event_webhook_signature

app = FastAPI(title="Reload Romania Roleplay")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()


@app.get("/")
async def home():
    return {"status": "online", "server": "Reload Romania Roleplay"}


@app.post("/erlc/events")
async def receive_event(request: Request):
    body = await request.body()

    try:
        assert_valid_event_webhook_signature(
            raw_body=body,
            headers=request.headers,
            max_skew_s=300,
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid ER:LC webhook signature",
        )

    if not DISCORD_WEBHOOK_URL:
        raise HTTPException(
            status_code=500,
            detail="Discord webhook is not configured",
        )

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")

    content = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(content) > 3800:
        content = content[:3700] + "\n... truncated"

    message = {
        "username": "Reload | ER:LC Logs",
        "allowed_mentions": {"parse": []},
        "embeds": [{
            "title": "ER:LC Event Log",
            "description": "
json\n" + content + "\n
"
        }]
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            DISCORD_WEBHOOK_URL,
            json=message
        )

    if response.status_code >= 300:
        raise HTTPException(
            status_code=502,
            detail="Discord delivery failed",
        )

    return {"received": True, "sent_to_discord": True}
