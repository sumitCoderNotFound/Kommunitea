"""Phase 4 Study Match AI assistant.

Optional by design. Without an API key it returns a clear rule-based explanation
built from the user's result, so the feature still works. With ANTHROPIC_API_KEY
set it can call the model for richer answers.
"""
import logging

from django.conf import settings

logger = logging.getLogger("kommunitea.studymatch")

SUPPORTED_INTENTS = {
    "explain_result", "compare_universities", "which_city", "next_steps",
    "application_checklist", "sop_checklist",
}


def _rule_based_answer(intent: str, result) -> str:
    if not result:
        return "Generate a Study Match first, then I can explain your results and next steps."
    if intent == "explain_result":
        top = (result.country_scores or [{}])[0]
        return (f"{result.overall_summary}\n\nYour top option to research is "
                f"{top.get('name', 'the UK')} (match {top.get('score', '')}/100). "
                "Open each country card to see academic, budget, career, visa and community scores explained.")
    if intent == "next_steps":
        wk = (result.action_plan or {}).get("this_week", [])
        return "This week: " + "; ".join(wk) if wk else "Shortlist universities, check English requirements, and estimate your budget."
    if intent == "application_checklist":
        return "Application checklist: shortlist universities → check entry + English requirements → prepare SOP → gather transcripts/passport/references → apply → track deadlines in Plan."
    if intent == "sop_checklist":
        return "SOP checklist: your motivation → academic background → why this course → why this university/UK → career goal → how it fits your plan → conclusion. Keep it specific and honest."
    if intent == "which_city":
        cities = result.city_recommendations or []
        if cities:
            c = cities[0]
            return f"{c['city']} scores well for you ({c['score']}/100): cost {c['cost_level']}, career market {c['career_market']}, community {c['community']}. Best for {c['best_for']}."
        return "Compare the city cards in your result — balance cost, job market and community."
    if intent == "compare_universities":
        return "Open the University Shortlist, save 2-3, then compare city, fees (official site), entry requirements and graduate job market."
    return "I can explain your result, compare options, or outline next steps. Generate a Study Match to begin."


def ai_assistant(intent: str, result, question: str = "") -> dict:
    intent = intent if intent in SUPPORTED_INTENTS else "explain_result"
    base = _rule_based_answer(intent, result)
    if not getattr(settings, "ANTHROPIC_API_KEY", ""):
        return {"answer": base, "source": "rule_based"}
    # Optional richer answer; never break if the call fails.
    try:
        import requests
        ctx = f"User question: {question}\nIntent: {intent}\nDraft guidance: {base}"
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 500,
                  "system": "You are Kommunitea's Study Match assistant for international students. Be concise, practical and never guarantee admission, visa or jobs. Recommend checking official sources.",
                  "messages": [{"role": "user", "content": ctx}]},
            timeout=15,
        )
        resp.raise_for_status()
        parts = [b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text"]
        return {"answer": "\n".join(parts).strip() or base, "source": "ai"}
    except Exception:
        logger.exception("Study Match AI call failed")
        return {"answer": base, "source": "rule_based"}
