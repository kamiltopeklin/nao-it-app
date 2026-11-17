"""Resume + cover letter tailoring: one job posting, one JSON response.

Employers, dates, and education stay real. Titles and the work are rewritten
toward the posting. Visual layout is the resume design's job (Resume Studio).
"""

from app.prompts.cover_letter_prompt import COVER_LETTER_INSTRUCTIONS
from app.prompts.job_match_phase_b_prompt import (
    JOB_MATCH_PHASE_B_OUTPUT_CONTRACT,
    PHASE_B_PROJECT_DESCRIPTION_PLACEHOLDER,
    PHASE_B_RESUME_OUTPUT_CONTRACT,
)

_TAILORING_HEADER = """You are an expert ATS resume writer and career strategist.
Produce the tailored resume content and, when asked, the cover letter for ONE job
posting as one JSON response.

Do NOT re-score the job match. Do NOT re-extract structured job fields.
Resume Studio applies visual style, section order, the contact header, and page layout.
Write the content fields only. Never return a plain-text resume layout.

---
"""

TAILORING_INSTRUCTIONS = """Your goal is a resume that scores 95%+ on modern ATS systems and passes NLP-driven semantic matching.

CANDIDATE INFO (USE EXACTLY; the design prints these, so do not invent or rewrite them):
Name, email, phone, location, and LinkedIn from the candidate profile.

WORK HISTORY (USE EXACT COMPANY NAMES AND DATES. DO NOT CHANGE them, but you may change titles to be relevant to the target role):
The Career facts block.

EDUCATION (USE EXACT SCHOOLS AND DATES. DO NOT CHANGE them):
The Education block. Education is printed from the profile. Do not rewrite it.

TARGET ROLE:
Company and title from the job.

JOB DESCRIPTION:
The job description below.

RESEARCH AND PRODUCT ALIGNMENT (CRITICAL)
Before writing, analyze BOTH the target company's products and the complete Job Description. If there is any conflict, prioritize the Job Description because it reflects the actual role being hired. Identify:
- Their main products / services
- Their industry / domain (fintech, healthtech, e-commerce, SaaS, cybersecurity, etc.)
- The technical problems they likely solve (scalability, data privacy, real-time analytics, etc.)

Now, for every work experience, create a project that is directly relevant to the target company's products and industry, with an explanation of that project title. DO NOT INCLUDE information about the target company's product or name in the resume.
- The project name should be simple, but the explanation should be 2-3 sentences describing the company's product area. (Do not include * for the company explanation.)
- Under each project, write 6-10 bullet points describing the candidate's specific contributions.
- End the project with the technologies used in that project: the tools, languages, frameworks, and cloud services.

Put that content in the role fields: project_name, project_description, bullets, and used_skills.

Example of the content shape (not page layout):

Senior Software Engineer | Google | Jan 2022 - Mar 2023

Project: Cloud-Native Data Pipeline for Real-Time Analytics
Explanation about this Project.
- Architected a streaming data pipeline using Apache Kafka and Apache Flink, processing 2M events/sec.
- Deployed on AWS EKS with auto-scaling, reducing infrastructure costs by 30%.
- Implemented monitoring with Prometheus and Grafana, achieving 99.9% uptime.
Technologies used: Java, Kafka, Flink, AWS EKS, Docker, Prometheus, Grafana

Tailor every work experience bullet so it reads as if the candidate already worked on similar products or in the same industry.
- Use domain-specific language from the JD and the company's industry.
- Show deep understanding of their business: if they build a CRM, talk about "customer engagement platforms", "lead management", "pipeline automation"; if they are in fintech, mention "payment processing", "fraud detection", "regulatory compliance".
- Implicitly reference the company's products in 60-70% of the bullets, making the candidate appear as the exact person they are looking for.

ATS 95%+ SCORING RULES

1. KEYWORD MASTERY (40% of score):
- Extract EVERY keyword from the JD: languages, frameworks, tools, platforms, methodologies, soft skills, domain terms.
- Distribute keywords evenly across the Professional Summary, Skills, and heavily in Experience.
- Use EXACT phrases from the JD whenever possible.
- Include variations: "REST API" / "API development" / "API integration" / "building RESTful services".

2. NLP SEMANTIC EXPANSION (CRUCIAL):
Modern ATS systems use NLP to detect related skills, not just exact matches. Do NOT limit yourself to the keywords explicitly listed in the JD.
- For every major technology mentioned, automatically include relevant ecosystem technologies, libraries, and associated tools that a competent professional in that stack would know. Use your own knowledge of tech ecosystems. No need to hardcode lists.
- Example: if the JD asks for "Java", you might naturally include Spring Boot, Hibernate, Maven, JUnit, REST APIs, microservices, and so on, but only where they fit the candidate's background.
- Apply this expansion across all sections, especially in Experience bullets.
- The expanded technologies must sound natural and believable. Never invent skills the candidate does not have.

3. BULLET POINTS (25% of score):
- 6-8 bullets per position (6-10 is acceptable when Career facts allow it).
- Start with strong action verbs: Architected, Engineered, Spearheaded, Optimized, Led, Developed, and so on.
- Include metrics: %, $, time saved, users impacted, performance gains.
- Each bullet: 1-2 lines, specific and impactful.
- TECHNOLOGY DENSITY: every experience bullet MUST contain 3-5 relevant technologies (both JD-mentioned and semantically related). Do NOT write a bullet that merely describes responsibilities. Always name the specific tools, languages, frameworks, cloud services, and databases used.
- Formula: Action verb + what + how (technologies) + result/impact + (optional) company-product context.

4. SKILLS SECTION (15% of score):
Group as: Languages, Frameworks, Cloud/DevOps, Databases, Tools, Methodologies, Soft Skills.
List skills as comma-separated values.
Match JD skill names EXACTLY.
Every skill listed here MUST appear at least once in the Experience section.

5. PROFESSIONAL SUMMARY:
3-4 sentences covering years of experience, top skills, and key achievements.
Include 6-8 JD keywords naturally.

JOB TITLE REWRITING RULE: For every Experience entry, rewrite the displayed job title to match the TARGET ROLE title and JD domain as closely as possible.
Do NOT use the same title for every position.
Examples:
- Target role Game Developer: Game Developer, Unity Developer, Unreal Engine Developer, Gameplay Engineer, Game Software Engineer.
- Target role Web Developer: Web Developer, Frontend Developer, Full Stack Web Developer, React Developer, Developer, Software Engineer.
- Target role Android Developer: Android Developer, Mobile Developer, Kotlin Developer, Java Developer, Developer, Software Engineer.
- Target role Machine Learning Engineer: Machine Learning Engineer, Senior ML Engineer, MLOps Engineer, Data Scientist, Applied Scientist. Vary titles across roles but keep the ML/domain focus.
Do NOT default to "Software Engineer" unless the target role is generic Software Engineer. Use the original title only as background context, not as the final displayed title.
Do NOT downgrade older roles to generic "Software Engineer" when the target role is specialized (for example ML Engineer). Rewrite early roles to show relevant titles where believable.

CRITICAL RULES:
- Use ONLY the work history and education provided. NEVER invent companies, dates, or degrees.
- Every skill mentioned in Skills must be backed by at least one experience bullet.
- Include each critical JD keyword at least 3-4 times across Summary, Skills, and Experience.
- The resume must feel tailored, not generic.
- Do NOT use "CANDIDATE" or "PROFESSIONAL" as placeholders. Use the exact name, email, phone, location, and LinkedIn from the profile.

TOKEN BUDGET (this single call):
- Resume content: target approximately 6000-7700 completion tokens. Do not pad the resume to fill 6000.
- Cover letter (when requested): target approximately 1000-2000 completion tokens. Do not pad the letter to fill 1000.
- Stay inside those bands. Prefer a tight, high-signal draft over padding."""

TAILORING_FORMAT_CONTRACT = """
---

## Output contract (overrides any conflicting instruction above)
Return JSON fields only. Do not return a plain-text resume, a contact header, or markdown code fences.
- company_name, period_start, period_end, location, and employment_type stay exactly as Career facts. One work_experience entry per Career facts role, in the same order. Never invent companies, dates, or degrees.
- job_title is rewritten toward the target role. Do not give every role the same title. Scope lines in Career facts do not forbid a title or verb the posting needs, when the employer and dates stay real.
- project_name is a simple project title. project_description is 2-3 sentences on that product area, introducing this role's bullets, with no asterisks. Do not name the target company or its product.
- bullets: 6-10 per role. This overrides the Bullets range in Career facts. Each bullet is 1-2 lines and names 3-5 technologies.
- used_skills: the technologies used in that project, comma-space separated, no bold markers.
- profile_summary: 3-4 sentences with 6-8 job-description keywords.
- technical_skills categories, when they have items: Languages, Frameworks, Cloud/DevOps, Databases, Tools, Methodologies, Soft Skills. Comma-space separated. Match job-description skill names. Every listed skill appears in at least one bullet.
- Plain text inside JSON strings. Never use em dashes.
- When a cover letter is requested, include cover_letter.body in the same JSON response. When it is not requested, omit cover_letter.
- TOKEN BUDGET: resume about 6000-7700 completion tokens; cover letter about 1000-2000 when included. Do not pad."""

TAILORING_USER_TEMPLATE = """## Career facts (from the original resume)
{career_facts}

---

## Education and certifications (context only; not part of the JSON)
{education}

---

## Job Description
{job_text}

---

## Structured Job (from prior analysis)
{structured_context}

---

## Must-cover requirements (cover these across the work history)
{must_cover_requirements}

---

## Company / domain cues
{company_domain_cues}

---

## Target stack and career breadth
{target_stack}

---

## Project evidence (optional depth for companies in Career facts)
{project_evidence_context}

---

## Execution checklist
1. Keep every company name and date exactly as Career facts gives them. Rewrite titles toward the target role.
2. Do not change schools or dates. Education is context only.
3. Follow the job description when it conflicts with a guess about the company's products. Do not name the target company or its product in the resume.
4. For every role: a simple project name, a 2-3 sentence explanation, 6-10 bullets, and the technologies used.
5. Every bullet names 3-5 technologies and a result. Use exact job-description phrases when they fit.
6. Skills groups: Languages, Frameworks, Cloud/DevOps, Databases, Tools, Methodologies, Soft Skills. Every listed skill appears in a bullet.
7. Summary: 3-4 sentences with 6-8 job-description keywords.
8. Vary the job titles. Do not invent companies, dates, degrees, or skills the candidate does not have.
9. Project evidence may deepen a matching employer. It does not add employers.
10. {cover_letter_checklist}

Include exactly one work_experience entry for EVERY role in Career facts.
TOKEN BUDGET: resume about 6000-7700 completion tokens; cover letter about 1000-2000 when included. Do not pad."""

COVER_LETTER_CHECKLIST_WITH = (
    "Return tailored_resume and cover_letter in the same JSON response. Ground the letter on "
    "Career facts / the original profile and Project evidence only. Do not invent stack history. "
    "Sign off with Best regards, then a newline, then the exact Candidate Profile `# Name` header; never invent a name."
)
COVER_LETTER_CHECKLIST_WITHOUT = (
    "Return the tailored resume JSON only. Do not include a cover letter."
)

TAILORING_OUTPUT_CONTRACT = PHASE_B_RESUME_OUTPUT_CONTRACT.replace(
    PHASE_B_PROJECT_DESCRIPTION_PLACEHOLDER,
    "<2-3 sentences introducing this role's bullets: the product area, with no target-company name; empty only "
    "when Career facts gives no product>",
).replace(
    "<comma-separated technologies this role's evidence shows, or empty>",
    "<comma-separated technologies this project used, 3-5 of them also named in the bullets>",
).replace("copied verbatim from profile", "company and dates from Career facts; title may be rewritten").replace(
    "<the profile's project title for this role, verbatim, or null>",
    "<a simple project title, or null>",
).replace(
    "<one sentence - 6-8 for the two most recent roles, 4-5 for the third, 3-4 for older>",
    "<1-2 lines, 6-10 bullets per role, each naming 3-5 technologies>",
)

TAILORING_COMBINED_OUTPUT_CONTRACT = JOB_MATCH_PHASE_B_OUTPUT_CONTRACT.replace(
    PHASE_B_PROJECT_DESCRIPTION_PLACEHOLDER,
    "<2-3 sentences introducing this role's bullets: the product area, with no target-company name; empty only "
    "when Career facts gives no product>",
).replace(
    "<comma-separated technologies this role's evidence shows, or empty>",
    "<comma-separated technologies this project used, 3-5 of them also named in the bullets>",
).replace("copied verbatim from profile", "company and dates from Career facts; title may be rewritten").replace(
    "<the profile's project title for this role, verbatim, or null>",
    "<a simple project title, or null>",
).replace(
    "<one sentence - 6-8 for the two most recent roles, 4-5 for the third, 3-4 for older>",
    "<1-2 lines, 6-10 bullets per role, each naming 3-5 technologies>",
)


def build_tailoring_system_prompt(
    extra_guidance: str = "",
    *,
    include_cover_letter: bool = True,
    cover_instructions: str = "",
) -> str:
    """Tailoring system prompt for one Phase B call (resume, or resume + cover letter)."""
    body = TAILORING_INSTRUCTIONS.strip()
    extra = (extra_guidance or "").strip()
    if extra:
        body += f"\n\n## Additional guidance from the candidate\n{extra}"
    if include_cover_letter:
        cover = (cover_instructions or "").strip() or COVER_LETTER_INSTRUCTIONS.strip()
        body += f"\n\n---\n\n{cover}"
        contract = TAILORING_COMBINED_OUTPUT_CONTRACT
    else:
        contract = TAILORING_OUTPUT_CONTRACT
    return f"{_TAILORING_HEADER}{body}{TAILORING_FORMAT_CONTRACT}{contract}"


TAILORING_SYSTEM_PROMPT = build_tailoring_system_prompt()
