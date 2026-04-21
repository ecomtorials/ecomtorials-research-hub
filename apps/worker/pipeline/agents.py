"""Agent utilities for the ecomtorials research pipeline.

Core primitive: drain_query() — validated pattern from content agent pipeline.
"""

import json
import os
import sys
import time
from contextvars import ContextVar
from typing import Any, Callable, Optional

import anyio
from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

# Optional activity emitter. Worker code installs a callback via
# set_activity_emitter(fn); drain_query reads the module-level variable
# and forwards every MCP tool_use block to it. We use a plain module-level
# var instead of a ContextVar because the Claude Agent SDK internals
# create background tasks whose contexts do not always inherit the caller's
# ContextVar state, so the emitter never got read. Single-worker Railway
# deployment means we run one job at a time — no concurrency hazard.
ActivityEmitter = Callable[[str, str, Any], None]
_current_emitter: Optional[ActivityEmitter] = None


def set_activity_emitter(fn: Optional[ActivityEmitter]) -> Optional[ActivityEmitter]:
    """Install the callback, return the previous one so callers can restore."""
    global _current_emitter
    prev = _current_emitter
    _current_emitter = fn
    return prev


def get_activity_emitter() -> Optional[ActivityEmitter]:
    return _current_emitter


# Kept for backward compatibility with any code that may still read the
# ContextVar; superseded by the module-level var above.
activity_emitter: ContextVar[Optional[ActivityEmitter]] = ContextVar(
    "activity_emitter", default=None
)


async def drain_query(
    prompt: str,
    options: ClaudeAgentOptions,
    agent_name: str = "?",
) -> tuple[str, float]:
    """Drain a query() async generator and return (result_text, cost_usd).

    CRITICAL: Do NOT use 'break' after ResultMessage. The SDK's internal anyio
    task group is created in a background asyncio task; calling aclose() from
    the outer task via 'break' triggers:
        RuntimeError('Attempted to exit cancel scope in a different task
        than it was entered in')
    Let the generator exhaust naturally.
    """
    result = ""
    cost = 0.0
    got_result = False
    all_text_parts: list[str] = []  # Collect ALL text blocks as fallback
    t0 = time.monotonic()

    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, ResultMessage):
                got_result = True
                structured = getattr(msg, "structured_output", None)
                if structured:
                    result = (
                        structured
                        if isinstance(structured, str)
                        else json.dumps(structured, ensure_ascii=False)
                    )
                else:
                    result = getattr(msg, "result", None) or ""

                # Fallback: if result empty, use collected text blocks
                if not result and all_text_parts:
                    result = "\n\n".join(all_text_parts)
                    print(f"[{agent_name}] Using TextBlock fallback ({len(all_text_parts)} parts)", file=sys.stderr)

                cost = getattr(msg, "total_cost_usd", None) or 0.0
                turns = getattr(msg, "num_turns", None)
                stop = getattr(msg, "stop_reason", None)

                elapsed = time.monotonic() - t0
                print(
                    f"[{agent_name}] Done: {len(result)} chars, "
                    f"${cost:.4f}, {turns} turns, {elapsed:.0f}s"
                    + (f" (stop: {stop})" if stop == "max_turns" else ""),
                    file=sys.stderr,
                )
                # NO break — let generator exhaust
            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        # Collect substantial text (>50 chars, skip tool confirmations)
                        if len(block.text.strip()) > 50:
                            all_text_parts.append(block.text)
                    elif hasattr(block, "type") and block.type == "tool_use":
                        tool_name = getattr(block, "name", "?")
                        tool_input = getattr(block, "input", {})
                        short = str(tool_input)[:60]
                        print(f"[{agent_name}] Tool: {tool_name}({short})", file=sys.stderr)
                        emitter = _current_emitter
                        if emitter is not None:
                            try:
                                emitter(agent_name, tool_name, tool_input)
                            except Exception as emit_err:  # noqa: BLE001
                                print(
                                    f"[activity-emitter-error/{agent_name}] {emit_err}",
                                    file=sys.stderr,
                                )
    except Exception as e:
        if got_result:
            print(f"[WARN/{agent_name}] Ignoring post-result error: {e}", file=sys.stderr)
        else:
            raise

    if not result and all_text_parts:
        result = "\n\n".join(all_text_parts)
        print(f"[{agent_name}] No ResultMessage — using {len(all_text_parts)} text parts", file=sys.stderr)

    if not result:
        print(f"[WARN/{agent_name}] Empty result!", file=sys.stderr)

    return result, cost


def make_research_options(
    system_prompt: str,
    cfg: dict,
    model: str = "claude-sonnet-4-6",
    effort: str = "medium",
    max_turns: int = 10,
    max_budget_usd: float = 3.0,
    tools: list[str] | None = None,
    mcp_servers: dict | None = None,
    output_format: dict | None = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for a research agent."""
    kwargs: dict = {
        "model": model,
        "allowed_tools": tools or ["WebSearch", "WebFetch"],
        "permission_mode": "auto",
        "max_turns": max_turns,
        "max_budget_usd": max_budget_usd,
        "system_prompt": system_prompt,
        "effort": effort,
    }
    if mcp_servers:
        kwargs["mcp_servers"] = mcp_servers
    if output_format:
        kwargs["output_format"] = output_format
    return ClaudeAgentOptions(**kwargs)


# ---------------------------------------------------------------------------
# Minimal self-test
# ---------------------------------------------------------------------------
async def _test_drain_query():
    """Minimal test: one drain_query() call to verify SDK works."""
    print("=== drain_query() Minimal-Test ===", file=sys.stderr)
    opts = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        allowed_tools=[],
        permission_mode="auto",
        max_turns=2,
        max_budget_usd=0.10,
        system_prompt="Du bist ein hilfreicher Assistent. Antworte kurz auf Deutsch.",
    )
    result, cost = await drain_query("Sage 'Hallo Welt' und sonst nichts.", opts, "test")
    print(f"Result: {result!r}", file=sys.stderr)
    print(f"Cost: ${cost:.4f}", file=sys.stderr)
    assert result, "drain_query() returned empty result!"
    print("=== Test PASSED ===", file=sys.stderr)
    return result, cost


async def _test_parallel():
    """Test: 2x drain_query() parallel via anyio task_group."""
    print("=== Parallel-Test (2x drain_query) ===", file=sys.stderr)
    opts = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        allowed_tools=[],
        permission_mode="auto",
        max_turns=2,
        max_budget_usd=0.10,
        system_prompt="Antworte mit genau einem Wort.",
    )
    results: list[tuple[str, float]] = [("", 0.0), ("", 0.0)]

    async def _a():
        results[0] = await drain_query("Sage 'Alpha'", opts, "parallel-A")

    async def _b():
        results[1] = await drain_query("Sage 'Beta'", opts, "parallel-B")

    t0 = time.monotonic()
    async with anyio.create_task_group() as tg:
        tg.start_soon(_a)
        tg.start_soon(_b)
    elapsed = time.monotonic() - t0

    print(f"A: {results[0][0]!r} (${results[0][1]:.4f})", file=sys.stderr)
    print(f"B: {results[1][0]!r} (${results[1][1]:.4f})", file=sys.stderr)
    print(f"Elapsed: {elapsed:.1f}s", file=sys.stderr)
    assert results[0][0] and results[1][0], "One or both parallel results empty!"
    print("=== Parallel Test PASSED ===", file=sys.stderr)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY in .env or environment", file=sys.stderr)
        sys.exit(1)

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--test", choices=["drain", "parallel", "all"], default="all")
    args = parser.parse_args()

    async def _run_tests():
        if args.test in ("drain", "all"):
            await _test_drain_query()
        if args.test in ("parallel", "all"):
            await _test_parallel()

    anyio.run(_run_tests)
