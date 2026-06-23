"""Tests for RRF fusion, pricing, extractors and the LLM message conversion."""
from __future__ import annotations

from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMMessage, ToolSpec
from app.llm.pricing import estimate_cost
from app.rag.extractors import extract
from app.rag.vectorstore import VectorHit, _rrf_merge


def test_rrf_merge_combines_rankings():
    a = [VectorHit("1", 0.9, {}), VectorHit("2", 0.8, {})]
    b = [VectorHit("2", 0.7, {}), VectorHit("3", 0.6, {})]
    merged = _rrf_merge(a, b, top_k=3)
    ids = [h.id for h in merged]
    assert ids[0] == "2"  # appears in both lists → highest fused score
    assert set(ids) == {"1", "2", "3"}


def test_pricing_estimate():
    cost = estimate_cost("claude-opus-4-8", 1_000_000, 1_000_000)
    assert round(cost, 2) == 30.00  # $5 in + $25 out


def test_extract_txt_and_json_and_csv():
    text, _ = extract("a.txt", b"hello world")
    assert "hello world" in text

    j, _ = extract("a.json", b'{"k": "v"}')
    assert '"k"' in j

    c, _ = extract("a.csv", b"a,b\n1,2")
    assert "a | b" in c


def test_anthropic_message_conversion_tool_roundtrip():
    p = AnthropicProvider(api_key="x", model="claude-opus-4-8")
    msgs = [
        LLMMessage(role="user", content="hi"),
        LLMMessage(
            role="assistant", content="let me check",
            tool_calls=[{"id": "t1", "name": "lookup", "arguments": {"q": "x"}}],
        ),
        LLMMessage(role="tool", content="result", tool_call_id="t1"),
    ]
    converted = p._to_anthropic_messages(msgs)
    assert converted[0] == {"role": "user", "content": "hi"}
    assert converted[1]["role"] == "assistant"
    assert any(b["type"] == "tool_use" for b in converted[1]["content"])
    assert converted[2]["content"][0]["type"] == "tool_result"


def test_anthropic_adaptive_thinking_only_without_tools():
    p = AnthropicProvider(api_key="x", model="claude-opus-4-8")
    tool = ToolSpec(name="lookup", description="d", input_schema={"type": "object"})
    with_tools = p._common_kwargs(None, [tool], 100, enable_thinking=True)
    without = p._common_kwargs(None, None, 100, enable_thinking=True)
    assert "thinking" not in with_tools
    assert without["thinking"] == {"type": "adaptive"}
