"""Thin wrapper around the Claude (Anthropic) or Gemini API, with retries and a mock mode.

Every LLM role in the study (Dr. Lee, judge, scorer, simulated learners) goes
through `generate()`, so the model, settings and logging live in one place.
"""
import json
import re
import time
from dataclasses import dataclass

from django.conf import settings

AGREED_RE = re.compile(r"\[\s*AGREED\s*\]", re.IGNORECASE)


class LLMError(Exception):
    pass


@dataclass
class LLMResult:
    text: str
    latency_ms: int
    model: str
    mock: bool = False


def cfg(key):
    return settings.STUDY[key]


_clients = {}


def _get_client():
    """Return a cached SDK client for the configured provider."""
    prov = cfg("PROVIDER")
    if prov not in _clients:
        if prov == "anthropic":
            import anthropic
            # The SDK's own retries are turned off; generate() retries so every attempt is logged the same way.
            _clients[prov] = anthropic.Anthropic(api_key=cfg("ANTHROPIC_API_KEY"), max_retries=0, timeout=30.0)
        elif prov == "gemini":
            from google import genai
            _clients[prov] = genai.Client(api_key=cfg("GEMINI_API_KEY"))
        else:
            raise LLMError(f"Unknown LLM_PROVIDER: {prov}")
    return _clients[prov]


def _thinking_config(types):
    value = str(cfg("THINKING") or "").strip()
    if not value:
        return None
    if value.lstrip("-").isdigit():
        return types.ThinkingConfig(thinking_budget=int(value))
    return types.ThinkingConfig(thinking_level=value)


def generate(system, history, temperature=0.7, as_json=False, max_tokens=1024, mock_fn=None, schema=None):
    """Call the model.

    system:  system instruction (string)
    history: list of (role, text) with role in {"user", "model"}; must start with "user"
    mock_fn: callable(system, history) -> str, used in mock mode
    schema:  optional JSON schema; with Claude it is enforced via structured outputs
    temperature: used by Gemini only (the current Claude API has no temperature parameter)
    """
    start = time.monotonic()
    if cfg("MOCK"):
        text = mock_fn(system, history) if mock_fn else "OK."
        return LLMResult(text=text, latency_ms=int((time.monotonic() - start) * 1000), model="mock", mock=True)

    call = _call_anthropic if cfg("PROVIDER") == "anthropic" else _call_gemini
    last_err = None
    for attempt in range(cfg("MAX_RETRIES") + 1):
        try:
            text = call(system, history, temperature, as_json, max_tokens, schema).strip()
            if not text:
                raise LLMError("Empty response (possibly blocked or out of output tokens)")
            return LLMResult(text=text, latency_ms=int((time.monotonic() - start) * 1000), model=cfg("MODEL"))
        except Exception as e:  # network, 429 rate limit, 5xx, overloaded, empty
            last_err = e
            if attempt < cfg("MAX_RETRIES"):
                time.sleep(1.5 * (attempt + 1))
    raise LLMError(f"LLM call failed after retries: {last_err}")


_downgraded = {"output_config": False}


def _call_anthropic(system, history, temperature, as_json, max_tokens, schema=None):
    import anthropic
    messages = [{"role": "assistant" if r == "model" else "user", "content": t} for r, t in history]
    if as_json:
        system = system + "\n\nRespond with a single JSON object and nothing else."
    output_config = {}
    if cfg("CLAUDE_EFFORT"):
        output_config["effort"] = cfg("CLAUDE_EFFORT")
    if as_json and schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    kwargs = dict(model=cfg("MODEL"), system=system, messages=messages, max_tokens=max_tokens)
    if output_config and not _downgraded["output_config"]:
        kwargs["output_config"] = output_config
    try:
        resp = _get_client().messages.create(**kwargs)
    except anthropic.BadRequestError as e:
        # If the chosen model rejects effort/format, fall back to a plain request (JSON is still asked for in the prompt).
        if "output_config" not in kwargs:
            raise
        _downgraded["output_config"] = True
        kwargs.pop("output_config")
        print(f"[llm] output_config rejected by {cfg('MODEL')}, continuing without it: {e}")
        resp = _get_client().messages.create(**kwargs)
    return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")


def _call_gemini(system, history, temperature, as_json, max_tokens, schema=None):
    from google.genai import types
    contents = [types.Content(role=r, parts=[types.Part(text=t)]) for r, t in history]
    kwargs = dict(system_instruction=system, temperature=temperature, max_output_tokens=max_tokens)
    if as_json:
        kwargs["response_mime_type"] = "application/json"
    thinking = _thinking_config(types)
    if thinking is not None:
        kwargs["thinking_config"] = thinking
    resp = _get_client().models.generate_content(model=cfg("MODEL"), contents=contents,
                                                 config=types.GenerateContentConfig(**kwargs))
    return resp.text or ""


def parse_json(text):
    """Parse a JSON object from model output, tolerating code fences."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.DOTALL)
    if not m:
        raise LLMError(f"No JSON object in output: {text[:200]}")
    return json.loads(m.group(0))


def strip_agreed(text):
    """Return (clean_text, agreed_flag)."""
    agreed = bool(AGREED_RE.search(text))
    return AGREED_RE.sub("", text).strip(), agreed
