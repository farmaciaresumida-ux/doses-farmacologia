from __future__ import annotations

import os
from datetime import date

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.newsletter_agent import NewsletterAgent


def _load_agent() -> NewsletterAgent:
    owner_contact = os.getenv("OWNER_TELEGRAM_CHAT_ID") or os.getenv("OWNER_WHATSAPP")
    if not owner_contact:
        owner_contact = "SEU_CHAT_ID"
    raw_groups = os.getenv("GROUP_IDS", "group-1,group-2")
    group_ids = [g.strip() for g in raw_groups.split(",") if g.strip()]
    business_context = os.getenv("BUSINESS_CONTEXT", "farmacologia prática")

    return NewsletterAgent(
        owner_number=owner_contact,
        group_ids=group_ids,
        business_context=business_context,
    )


app = FastAPI(title="Newsletter Agent")
agent = _load_agent()


def _status_text() -> str:
    s = agent.delivery_status()
    return (
        "📡 Status da integração\n"
        f"- Telegram: {'ativo' if s['telegram_enabled'] else 'inativo'}\n"
        f"- Z-API: {'ativo' if s['zapi_enabled'] else 'inativo'}\n"
        f"- Grupos configurados: {s['group_count']}"
    )


class ApprovalIn(BaseModel):
    draft_id: str
    approved: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/status")
def status() -> dict:
    return agent.delivery_status()


@app.post("/test-real")
def test_real() -> dict:
    try:
        return agent.test_real_delivery()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha no teste real: {exc}") from exc


@app.post("/run-daily")
def run_daily() -> dict:
    draft = agent.daily_scheduler(date.today())
    return {
        "draft_id": draft.draft_id,
        "kind": draft.kind,
        "topics": draft.topics,
        "preview": draft.content[:220],
    }


@app.post("/approval")
def approval(payload: ApprovalIn) -> dict:
    try:
        draft = agent.set_approval(payload.draft_id, payload.approved)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"draft_id": draft.draft_id, "approved": draft.approved, "kind": draft.kind}


@app.post("/telegram/webhook")
def telegram_webhook(payload: dict) -> dict:
    message = payload.get("message") or payload.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    chat_id = str((message.get("chat") or {}).get("id") or "")

    if not chat_id:
        return {"ok": True, "ignored": True}

    if text.startswith("/start"):
        agent.telegram.send_message(
            chat_id,
            "✅ Bot online!\nComandos: /status, /test-real, /run-daily",
        )
        return {"ok": True, "command": "/start"}

    if text.startswith("/status"):
        agent.telegram.send_message(chat_id, _status_text())
        return {"ok": True, "command": "/status"}

    if text.startswith("/test-real"):
        result = agent.test_real_delivery()
        agent.telegram.send_message(chat_id, f"Teste executado: {result}")
        return {"ok": True, "command": "/test-real"}

    if text.startswith("/run-daily"):
        draft = agent.daily_scheduler(date.today())
        agent.telegram.send_message(chat_id, f"Draft criado: {draft.draft_id} ({draft.kind})")
        return {"ok": True, "command": "/run-daily"}

    agent.telegram.send_message(chat_id, "Comandos disponíveis: /start, /status, /test-real, /run-daily")
    return {"ok": True, "command": "unknown"}
