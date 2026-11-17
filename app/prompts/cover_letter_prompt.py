"""Default instructions for AI cover letter body generation (Phase B, Task 2)."""

COVER_LETTER_PROMPT_MIN_LENGTH = 50
COVER_LETTER_PROMPT_MAX_LENGTH = 12000

_COVER_LETTER_LINES = (
    "## Cover letter",
    "",
    "Write a complete cover letter body as a single string. Separate the greeting, each body paragraph, and the sign-off with a blank line (`\\n\\n`).",
    "",
    "TOKEN BUDGET: about 1000-2000 completion tokens for the cover letter in this call. It is not the length of the letter. Write the 3-4 paragraph letter described below. Do not pad the letter to fill 1000 tokens. Stay inside 1000-2000.",
    "",
    "### Required structure (exact order)",
    "1. Greeting line: `Hi Hiring Manager,`",
    "2. 3-4 body paragraphs anchored to this role.",
    "3. Sign-off block: `Best regards,` then a newline (`\\n`) then the candidate's exact full name from the Candidate Profile header (the `# Name` line).",
    "",
    "Use a single `\\n` only inside the sign-off, between `Best regards,` and the name.",
    "",
    "### What the letter does",
    "- Name the hiring company and the target role.",
    "- Before writing, use the job description first. If a guess about the company's products conflicts with the job description, follow the job description.",
    "- Use domain language from the job description and that industry (for a CRM: customer engagement, lead management, pipeline automation; for fintech: payment processing, fraud detection, regulatory compliance).",
    "- Use exact phrases from the job description when they fit a sentence, and close variations of the same skill.",
    "- For a technology the posting names, you may also name related tools a competent person in that stack would use, only where the candidate's real background supports them.",
    "- Tie the candidate's employers, dates, and work to what the posting asks for. Show overlap. Do not claim the candidate built the target company's own product.",
    "- Do not pad with generic praise for the company.",
    "",
    "### Tone",
    "- Realistic and polite, in the candidate's own voice, not a marketing brochure.",
    "- Plain, direct sentences. One clear point per paragraph.",
    "- Never use em dashes.",
    "- No buzzword stacks, and no empty superlatives (thrilled, passionate, perfect fit).",
    "",
    "### Output rules",
    "- Start with the greeting and end with the sign-off. Do not include contact details, an address, the company address, or the date. The letterhead already has those.",
    "- The sign-off name must match the Candidate Profile `# Name` header exactly (first + last as written there).",
    "- Never invent a name. Never use placeholders or sample names such as Candidate, Candidate Name, [Name], CANDIDATE, PROFESSIONAL, Jane Doe, John Doe, or any other made-up person.",
    "- Never invent employers, dates, degrees, skills, or metrics that the profile and project evidence do not support.",
    "- When this call also returns a tailored resume, put the letter in cover_letter.body of the same JSON. When this call is cover-letter-only, return only the cover letter JSON.",
)

COVER_LETTER_INSTRUCTIONS = "\n".join(_COVER_LETTER_LINES)


def get_cover_letter_prompt_defaults() -> dict[str, int | str]:
    return {
        "default_instructions": COVER_LETTER_INSTRUCTIONS.strip(),
        "max_length": COVER_LETTER_PROMPT_MAX_LENGTH,
        "min_length": COVER_LETTER_PROMPT_MIN_LENGTH,
    }
