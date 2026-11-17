"""Cover letter sign-off must use the real profile name, not LLM placeholders."""

from app.services.job_match_service import _parse_cover_letter
from app.utils.cover_letter_text import candidate_name_from_profile_text, fix_cover_letter_signoff


def test_candidate_name_from_profile_h1():
    text = "# Ada Lovelace\nSoftware Engineer\n## Summary\nBuilt engines."
    assert candidate_name_from_profile_text(text) == "Ada Lovelace"


def test_candidate_name_skips_section_headers():
    assert candidate_name_from_profile_text("## Summary\nHello") == ""
    assert candidate_name_from_profile_text("") == ""


def test_fix_signoff_replaces_placeholder_names():
    body = (
        "Hi Hiring Manager,\n\n"
        "I am excited about the role.\n\n"
        "Best regards,\nJane Doe"
    )
    fixed = fix_cover_letter_signoff(body, "Ada Lovelace")
    assert fixed.endswith("Best regards,\nAda Lovelace")
    assert "Jane Doe" not in fixed
    assert fixed.startswith("Hi Hiring Manager,")


def test_fix_signoff_replaces_candidate_placeholders():
    for fake in ("Candidate", "Candidate Name", "Przemyslaw Kowalski", "[Name]"):
        body = f"Hi Hiring Manager,\n\nParagraph.\n\nBest regards,\n{fake}"
        fixed = fix_cover_letter_signoff(body, "Sam Rivera")
        assert fixed.endswith("Best regards,\nSam Rivera")
        assert fake not in fixed


def test_fix_signoff_appends_when_missing():
    body = "Hi Hiring Manager,\n\nI build payment systems."
    assert fix_cover_letter_signoff(body, "Sam Rivera") == (
        "Hi Hiring Manager,\n\nI build payment systems.\n\nBest regards,\nSam Rivera"
    )


def test_fix_signoff_noop_without_name():
    body = "Hi Hiring Manager,\n\nHello.\n\nBest regards,\nJane Doe"
    assert fix_cover_letter_signoff(body, "") == body
    assert fix_cover_letter_signoff(body, "   ") == body


def test_parse_cover_letter_rewrites_signoff_from_profile_name():
    parsed = _parse_cover_letter(
        {"body": "Hi Hiring Manager,\n\nFit is strong.\n\nBest regards,\nCandidate Name"},
        candidate_name="Alex Chen",
    )
    assert parsed == {
        "body": "Hi Hiring Manager,\n\nFit is strong.\n\nBest regards,\nAlex Chen",
    }
