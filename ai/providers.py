"""
AI provider abstraction.

Swap providers by changing AI_PROVIDER in .env. Today: OpenAI.
Later: add an 'ollama' branch here to use a local model — the rest of the
app (services, views) never changes.
"""
from decouple import config

AI_PROVIDER = config("AI_PROVIDER", default="openai")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4o-mini")


def ai_enabled() -> bool:
    """True when a real model is configured. If False, services fall back
    to non-AI heuristics so the feature still works for MVP/dev."""
    if AI_PROVIDER == "openai":
        return bool(OPENAI_API_KEY)
    if AI_PROVIDER == "ollama":
        return True
    return False


def complete(system: str, user: str, max_tokens: int = 700, temperature: float = 0.7) -> str:
    """Send a prompt to the configured provider and return the text reply."""
    if AI_PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    if AI_PROVIDER == "ollama":
        # Placeholder for local model support (e.g. via the ollama python client).
        import requests
        base = config("OLLAMA_URL", default="http://localhost:11434")
        model = config("OLLAMA_MODEL", default="llama3")
        r = requests.post(f"{base}/api/chat", json={
            "model": model, "stream": False,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }, timeout=60)
        return r.json().get("message", {}).get("content", "")

    raise RuntimeError(f"Unknown AI_PROVIDER: {AI_PROVIDER}")
