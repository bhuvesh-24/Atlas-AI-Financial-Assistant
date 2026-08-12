from __future__ import annotations
import json
import logging
from typing import List, Dict, Any, Optional
from config import settings
from ai.prompts import SYSTEM_PROMPT, ONBOARDING_PROMPT, DOCUMENT_SUMMARY_PROMPT
from ai.tools import get_tool_definitions, dispatch_tool
from ai.memory import build_user_context, get_recent_messages
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _is_retryable(err: Exception) -> bool:
    s = str(err).lower()
    return any(x in s for x in [
        "rate limit", "429", "quota", "over capacity", "tokens",
        "tool_use_failed", "tool call validation", "resource_exhausted",
        "model_decommissioned", "not found", "timeout",
    ])


async def generate_response(
    session: AsyncSession,
    user,
    user_message: str,
    message_type: str = "text",
    document_text: Optional[str] = None,
) -> str:
    history = await get_recent_messages(session, user.id, limit=8)
    context = build_user_context(user)

    if not user.onboarding_complete:
        system = ONBOARDING_PROMPT.format(
            onboarding_step=user.onboarding_step or "welcome",
            known_profile=context,
        )
    else:
        system = SYSTEM_PROMPT.format(user_context=context)

    if document_text:
        system += "\n\n" + DOCUMENT_SUMMARY_PROMPT.format(
            document_text=document_text[:25000]
        )

    messages = [
        {"role": "user" if m["role"] == "user" else "assistant", "content": m["content"]}
        for m in history
    ]
    messages.append({"role": "user", "content": user_message})
    tools = get_tool_definitions(google_connected=bool(user.google_connected))

    providers = _provider_chain()
    if not providers:
        return "No LLM API keys configured. Set GROQ_API_KEY and/or OPENROUTER_API_KEY in .env"

    errors = []
    for name, runner in providers:
        try:
            return await runner(session, user, system, messages, tools)
        except Exception as e:
            logger.warning("%s failed: %s", name, e)
            errors.append(f"{name}: {e}")
            if not _is_retryable(e):
                continue

    return "All providers failed or hit limits:\n" + "\n".join(errors[:5])


def _provider_chain():
    chain = []
    pref = (settings.LLM_PROVIDER or "auto").lower()

    if pref == "groq" and settings.GROQ_API_KEY:
        chain.append(("groq", _run_groq))
    elif pref == "openrouter" and settings.OPENROUTER_API_KEY:
        chain.append(("openrouter", _run_openrouter))
    else:
        # auto: Groq first, then OpenRouter
        if settings.GROQ_API_KEY:
            chain.append(("groq", _run_groq))
        if settings.OPENROUTER_API_KEY:
            chain.append(("openrouter", _run_openrouter))
    return chain


async def _run_openai_compatible(
    session,
    user,
    system: str,
    messages: List[Dict],
    tools: List,
    *,
    api_key: str,
    base_url: str,
    model: str,
    extra_headers: Optional[Dict] = None,
) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers=extra_headers or {},
    )

    oai_tools = []
    tool_names = set()
    for t in tools:
        name = t["name"]
        tool_names.add(name)
        schema = dict(t.get("input_schema") or {"type": "object", "properties": {}})
        schema.setdefault("type", "object")
        schema.setdefault("properties", {})
        oai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": (t.get("description") or "")[:500],
                "parameters": schema,
            },
        })

    oai_messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]

    max_rounds = 4
    for _ in range(max_rounds):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=oai_messages,
                tools=oai_tools if oai_tools else None,
                tool_choice="auto",
                max_tokens=1536,
                temperature=0.3,
            )
        except Exception as e:
            if "tool" in str(e).lower():
                resp = client.chat.completions.create(
                    model=model,
                    messages=oai_messages,
                    max_tokens=1536,
                    temperature=0.4,
                )
                return (resp.choices[0].message.content or "").strip() or (
                    "I'm here — what would you like to dig into?"
                )
            raise

        msg = resp.choices[0].message
        if not getattr(msg, "tool_calls", None):
            return (msg.content or "").strip() or "I'm here — what would you like to dig into?"

        tool_calls_payload = []
        for tc in msg.tool_calls:
            raw_name = (tc.function.name or "").strip()
            name = raw_name.split("{")[0].split("(")[0].strip()
            if name not in tool_names:
                continue
            args_str = tc.function.arguments or "{}"
            if "{" in raw_name and raw_name != name:
                try:
                    args_str = raw_name[raw_name.index("{"):]
                except Exception:
                    pass
            tool_calls_payload.append({
                "id": tc.id,
                "type": "function",
                "function": {"name": name, "arguments": args_str},
            })

        if not tool_calls_payload:
            return (msg.content or "").strip() or "I'm here — what would you like to dig into?"

        oai_messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": tool_calls_payload,
        })

        for tc_payload in tool_calls_payload:
            name = tc_payload["function"]["name"]
            try:
                args = json.loads(tc_payload["function"]["arguments"] or "{}")
            except Exception:
                args = {}
            if not isinstance(args, dict):
                args = {}
            result = await dispatch_tool(name, args, user, session)
            oai_messages.append({
                "role": "tool",
                "tool_call_id": tc_payload["id"],
                "content": json.dumps(result, default=str)[:8000],
            })

    return "I hit a complexity limit — try a narrower question."


async def _run_groq(session, user, system, messages, tools):
    return await _run_openai_compatible(
        session, user, system, messages, tools,
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        model=settings.GROQ_MODEL,
    )


async def _run_openrouter(session, user, system, messages, tools):
    return await _run_openai_compatible(
        session, user, system, messages, tools,
        api_key=settings.OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
        model=settings.OPENROUTER_MODEL,
        extra_headers={
            "HTTP-Referer": "https://t.me/AtlasFinanceBot",
            "X-Title": "Atlas Financial Assistant",
        },
    )