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


class ApprovalIn(BaseModel):
    draft_id: str
    approved: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
