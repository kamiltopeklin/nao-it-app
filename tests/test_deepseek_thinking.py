from app.core.llm_client import _apply_tailoring_thinking_policy


def test_deepseek_disables_thinking_and_drops_effort():
    out = _apply_tailoring_thinking_policy(
        {
            "model": "deepseek-flash",
            "reasoning_effort": "low",
            "max_tokens": 100,
        },
        model="deepseek-flash",
        base_url="https://api.deepseek.com/v1",
    )
    assert "disable_deepseek_thinking" not in out
    assert "reasoning_effort" not in out
    assert out["extra_body"]["thinking"] == {"type": "disabled"}
    assert out["max_tokens"] == 100


def test_deepseek_disables_thinking_without_legacy_flag():
    out = _apply_tailoring_thinking_policy(
        {"max_tokens": 16},
        model="deepseek-flash",
        base_url="https://api.deepseek.com/v1",
    )
    assert out["extra_body"]["thinking"] == {"type": "disabled"}
    assert out["max_tokens"] == 16


def test_legacy_flag_is_stripped_on_openai():
    out = _apply_tailoring_thinking_policy(
        {"disable_deepseek_thinking": True, "reasoning_effort": "low"},
        model="gpt-5.1",
        base_url="https://api.openai.com/v1",
    )
    assert "disable_deepseek_thinking" not in out
    assert "extra_body" not in out
    assert out["reasoning_effort"] == "low"


def test_openai_endpoint_keeps_thinking_params():
    out = _apply_tailoring_thinking_policy(
        {"max_tokens": 16, "reasoning_effort": "medium"},
        model="gpt-5.1",
        base_url="https://api.openai.com/v1",
    )
    assert out == {"max_tokens": 16, "reasoning_effort": "medium"}
