"""Friendly, page-aware civic guide owned by WeThePeople."""

import json
import logging
import os
import re
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services.auth import get_client_ip
from services.rate_limit_store import check_rate_limit


logger = logging.getLogger(__name__)
router = APIRouter(tags=["guide"])

GUIDE_LIMIT = int(os.getenv("WTP_GUIDE_FREE_LIMIT", "20"))
GUIDE_WINDOW_SECONDS = 86400

GUIDE_SYSTEM_PROMPT = """You are WTP Guide, the friendly navigation assistant built into WeThePeople.
Your user may be confused and may not know what to ask. Help them understand the current page and choose one useful next step.

Rules:
- Use plain, warm language. Keep answers under 120 words unless the user asks for detail.
- Start with the direct answer. Avoid jargon and explain any civic term you must use.
- Be nonpartisan. Never favor a party, candidate, ideology, or election outcome.
- Never invent election details, officials, dates, statistics, or page capabilities.
- Ask at most one short follow-up question, and only when it is truly needed.
- When a WTP page is the best next step, end with exactly one action line using valid JSON:
  ACTION:{"type":"navigate","path":"/path"}
- Useful routes: /act (take civic action), /elections (plan a vote), /politics/find-rep (find representatives), /civic (agenda), /videos (watch), /forecasts (civic forecasts), /methodology (sources).
- Do not claim that an action was completed. Say what the user can do next.
"""


class GuideRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    context: Optional[dict] = None


class GuideAction(BaseModel):
    type: str
    path: Optional[str] = None
    query: Optional[str] = None


class GuideResponse(BaseModel):
    answer: str
    action: Optional[GuideAction] = None
    cached: bool = False


def _fallback_guide(question: str, page: str) -> dict:
    """Keep the guide useful when the optional model provider is unavailable."""
    prompt = question.casefold()
    if page.startswith("/act") or any(word in prompt for word in ("act", "this page", "looking at")):
        return {
            "answer": (
                "This page helps you do two things: make a voting plan and find the people who represent you. "
                "Start with your state and ZIP. Your ZIP carries into the representatives step automatically, "
                "and nothing is sent to an office unless you choose to send it."
            ),
            "action": {"type": "navigate", "path": "/act"},
        }
    if any(word in prompt for word in ("vote", "ballot", "polling", "election")):
        return {
            "answer": "Start with your state, then enter your ZIP and street address to check available official election details. Always confirm the final information with your state or local election office.",
            "action": {"type": "navigate", "path": "/elections"},
        }
    if any(word in prompt for word in ("representative", "reps", "senator", "congress")):
        return {
            "answer": "Enter your five-digit ZIP to see your U.S. House member and senators. You can review each person before deciding whether to contact an office.",
            "action": {"type": "navigate", "path": "/politics/find-rep"},
        }
    if any(word in prompt for word in ("source", "verify", "trust", "method")):
        return {
            "answer": "Use the source links shown with each claim or result, then compare the information with the original government or publisher page. Our methodology explains how WeThePeople handles sources.",
            "action": {"type": "navigate", "path": "/methodology"},
        }
    return {
        "answer": "You do not need to know the right civic words. Tell me whether you want to plan a vote, find your representatives, understand an issue, or check a source, and I’ll point you to the next step.",
        "action": {"type": "navigate", "path": "/act"},
    }


def _remaining(ip: str) -> int:
    from models.database import get_db
    from services.rate_limit_store import RateLimitRecord

    db = next(get_db())
    try:
        cutoff = time.time() - GUIDE_WINDOW_SECONDS
        count = db.query(RateLimitRecord).filter(
            RateLimitRecord.ip_address == ip,
            RateLimitRecord.endpoint == "guide",
            RateLimitRecord.window_start >= cutoff,
        ).count()
        return max(0, GUIDE_LIMIT - count)
    finally:
        db.close()


def _call_guide(question: str, page: str) -> dict:
    from services.budget import check_budget, compute_cost, log_token_usage, record_spend
    from services.llm.client import get_llm_client

    allowed, _ = check_budget(estimated_cost=0.005)
    if not allowed:
        raise HTTPException(status_code=503, detail="Your guide is taking a short break. Please try again later.")

    model = "claude-haiku-4-5-20251001"
    client = get_llm_client()
    response = client.messages.create(
        model=model,
        max_tokens=350,
        system=GUIDE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"[Current WTP page: {page}]\n\n{question}"}],
    )
    text = response.content[0].text.strip() if response.content else "I couldn't prepare a helpful answer just now."
    action = None
    answer_lines = []
    for line in text.splitlines():
        if line.strip().startswith("ACTION:"):
            try:
                candidate = json.loads(line.strip()[7:])
                path = str(candidate.get("path") or "")
                if candidate.get("type") == "navigate" and path.startswith("/") and not path.startswith("//"):
                    action = {"type": "navigate", "path": path}
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        else:
            answer_lines.append(line)

    if hasattr(response, "usage") and response.usage:
        input_tokens = getattr(response.usage, "input_tokens", 0) or 0
        output_tokens = getattr(response.usage, "output_tokens", 0) or 0
        cost = compute_cost(model, input_tokens, output_tokens)
        record_spend(cost, model, input_tokens, output_tokens)
        log_token_usage("wtp_guide", model, input_tokens, output_tokens, cost, question[:100])

    return {"answer": "\n".join(answer_lines).strip() or "Here’s the next step.", "action": action}


@router.post("/ask", response_model=GuideResponse)
def ask_guide(body: GuideRequest, request: Request):
    client_ip = get_client_ip(request)
    allowed, _, _ = check_rate_limit(
        ip=client_ip,
        endpoint="guide",
        max_requests=GUIDE_LIMIT,
        window_seconds=GUIDE_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="You’ve reached today’s guide limit. Please come back tomorrow.")

    page = re.sub(r"[^a-zA-Z0-9/_-]", "", str((body.context or {}).get("page") or "/"))[:80]
    try:
        result = _call_guide(body.question.strip(), page)
    except HTTPException:
        raise
    except ValueError as exc:
        logger.info("WTP Guide using built-in fallback: %s", type(exc).__name__)
        result = _fallback_guide(body.question.strip(), page)
    except Exception as exc:
        logger.error("WTP Guide request failed: %s", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Your guide could not answer just now. Please try again.") from exc
    return GuideResponse(
        answer=result["answer"],
        action=GuideAction(**result["action"]) if result.get("action") else None,
    )


@router.get("/remaining")
def guide_remaining(request: Request):
    try:
        remaining = _remaining(get_client_ip(request))
    except Exception as exc:
        logger.warning("Guide limit check failed: %s", type(exc).__name__)
        remaining = GUIDE_LIMIT
    return {"remaining": remaining, "limit": GUIDE_LIMIT}
