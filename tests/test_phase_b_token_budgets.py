from app.services.job_match_service import (
    _COVER_LETTER_MAX_TOKENS_MAX,
    _COVER_LETTER_MAX_TOKENS_MIN,
    _RESUME_MAX_TOKENS_MAX,
    _RESUME_MAX_TOKENS_MIN,
    _cover_letter_max_tokens,
    _phase_b_resume_max_tokens,
)


def test_resume_budget_clamped_to_band(monkeypatch):
    monkeypatch.setattr(
        "app.services.job_match_service.get_effective_value_sync",
        lambda key: 16384 if key == "phase_b_max_tokens" else None,
    )
    assert _phase_b_resume_max_tokens() == _RESUME_MAX_TOKENS_MAX

    monkeypatch.setattr(
        "app.services.job_match_service.get_effective_value_sync",
        lambda key: 1000 if key == "phase_b_max_tokens" else None,
    )
    assert _phase_b_resume_max_tokens() == _RESUME_MAX_TOKENS_MIN

    monkeypatch.setattr(
        "app.services.job_match_service.get_effective_value_sync",
        lambda key: 7000 if key == "phase_b_max_tokens" else None,
    )
    assert _phase_b_resume_max_tokens() == 7000


def test_cover_letter_budget_clamped_to_band(monkeypatch):
    class _S:
        cover_letter_max_tokens = 4096

    monkeypatch.setattr("app.services.job_match_service.get_settings", lambda: _S())
    assert _cover_letter_max_tokens() == _COVER_LETTER_MAX_TOKENS_MAX

    class _Low:
        cover_letter_max_tokens = 200

    monkeypatch.setattr("app.services.job_match_service.get_settings", lambda: _Low())
    assert _cover_letter_max_tokens() == _COVER_LETTER_MAX_TOKENS_MIN
