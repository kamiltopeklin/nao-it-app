# NAO feature map

Every product feature, the order it runs in, the code that owns it, and the outside service it calls. Scoring is local vectors. OpenAI is the default only where a section says LLM.

## System tree

```text
NAO
├─ Account
│  ├─ Landing, privacy, terms
│  ├─ Password session and Google OAuth
│  └─ Onboarding
├─ Profile
│  ├─ Profile editor
│  ├─ Resume file parse (LLM)
│  ├─ Project source documents (LLM)
│  └─ Original resume file (skip rewrite)
├─ Job intake
│  ├─ Paste URL
│  ├─ Paste description
│  ├─ Saved sources and site connections
│  ├─ Admin spiders
│  └─ Attachment URL extraction (LLM)
├─ Extraction
│  └─ Fetch and normalize the posting
├─ Match
│  ├─ Job encoding (local MiniLM)
│  ├─ Profile encoding (local MiniLM)
│  ├─ Free score (vectors + cross-encoder)
│  ├─ Optional LLM quality check
│  ├─ Score floor and duplicates
│  ├─ Auto-score on visit
│  └─ Save and websocket
├─ Tailoring
│  ├─ Resume prompt (OpenAI by default)
│  ├─ Cover letter prompt (separate call)
│  ├─ Project description repair
│  ├─ DOCX and PDF build
│  └─ Resume studio (layout only)
├─ Workspace
│  ├─ Home, Jobs, Insights, Documents
│  ├─ Natural language search (LLM to SQL)
│  └─ Preferences
├─ Interviews
│  ├─ Nylas mailbox
│  ├─ Stage pipeline (LLM classifies mail)
│  └─ Shared reports
├─ Assistant
│  └─ Streaming chat and tools, including tailor
├─ Integrations
│  ├─ Chrome extension and autofill (LLM)
│  ├─ Google Sheets
│  └─ Pumble
├─ Plans and team
│  ├─ Credits and packages (no payment provider)
│  └─ Team space
├─ Admin
│  ├─ Pipeline, data, users
│  ├─ LLM keys and per-job bindings
│  ├─ Match engine diagnose
│  └─ Logs
└─ Runtime
   └─ FastAPI, eight worker queues, Postgres, Redis, nginx
```

## Job pipeline, in order

Preferences can stop this after extraction, or after the score.

```text
You add a job
  paste URL | paste text | extension | board sync | scraper
        |
        v
Extraction (queue job_extraction)
  career-site API, HTML, or Playwright
  cleaner, work mode, clearance check
        |
        v
Encode job (queue job_encoding)
  local MiniLM vectors + cross-encoder digest
        |
        v
Free match score (queue job_analysis)
  vector_match v5 + optional local cross-encoder
  no OpenAI on this step
        |
        +-- LLM quality check, only if that preference is on
        |
        v
Save (queue job_save)
  score floor, duplicate hide, websocket refresh
        |
        +-- Autopost (queue job_autopost): Google Sheets, Pumble
        |
        v
Tailor (queue job_tailoring), only in full pipeline
  evidence pack from project docs
  resume prompt (job_first or evidence)
  cover letter prompt (separate call)
  optional project-description repair
        |
        v
Document build (queue resume_build)
  DOCX and PDF from the template
        |
        v
Documents page, extension autofill, interviews if mail says you applied
```

## Outside services

| Service | Used by | Not used by |
| --- | --- | --- |
| OpenAI (default LLM) | Tailor, cover letter, quality check, resume parse, evidence, assistant, autofill, interview mail, AI search | Free match score, embeddings, document render |
| Anthropic, Gemini | Fallback, or the provider an admin binding selects for a job type | Anything still bound to OpenAI |
| MiniLM embeddings | Job encoding, profile encoding, requirement-match check inside tailor retries | Writing the resume prose |
| Cross-encoder nao-match-ce-v5 | Free match score when weights and CUDA are available | Tailor and cover letter |
| Career sites and board APIs | Extraction and scrapers (Greenhouse, Lever, Ashby, Workday, Indeed RapidAPI, Adzuna, and the other plugins) | Scoring and writing |
| Playwright Chromium | Browser extractor and some spiders | LLM calls |
| Nylas | Mailbox sync and interview pipeline | Job scoring |
| Google Sheets | Autopost after save | Tailor |
| Pumble | Autopost after save | Tailor |
| Google OAuth | Sign-in | Job pipeline |
| Postgres | All stored state |  |
| Redis | Queues, save lock, websocket pubsub, token denylist |  |

## Feature index

| Feature | Area | Runs after | External service |
| --- | --- | --- | --- |
| Landing, privacy, terms | Account | Nothing. These routes do not require a session. | None. Static frontend. |
| Password login and session | Account | An active account with a password hash. | None. Postgres stores the user. Redis holds the denylist when configured. |
| Google sign-in | Account | Google OAuth client id and secret in server config. | Google OAuth. |
| Onboarding | Account | A signed-in account with an empty profile. | Resume upload uses the resume_parse LLM job. Encoding uses the local MiniLM model. |
| Profile editor | Profile | A signed-in user. | None for a manual edit. Encoding is local. |
| Resume upload parse | Profile | A PDF or document on the profile or onboarding screen. | LLM via get_llm_client_for_user, job type resume_parse. Default provider OpenAI, model from the job binding or openai_model. |
| Project source documents | Profile | Completed uploads on the profile. | Two LLM jobs: profile_source_doc, then later profile_evidence. No vector search in this step. |
| Original resume file | Profile | Preferences, Matching, Resume for applications is set to the original file. | Cover letter LLM call only (job type resume_tailoring). No resume-rewrite prompt. |
| Paste a job URL | Job intake | Signed-in user. Pipeline mode in Preferences decides how far the job runs. | None until extraction. The page fetch happens in the next feature. |
| Paste a job description | Job intake | Raw description text from the user or the assistant. | Local embeddings (MiniLM). LLM only if a later tailor or quality check is requested. |
| Saved job sources and site connections | Job intake | A source or site connection saved under Integrations or admin job sync. | Board APIs: Indeed via RapidAPI, Adzuna, Welcome to the Jungle Algolia, Remote Rocketship, Jobright, JSearch, Fantastic Jobs, Jobicy, Glassdoor, LinkedIn scraper plugin. |
| Admin scraper spiders | Job intake | An admin starts a spider or the schedule fires. | Those job boards over HTTP. Playwright is used when a spider or extractor needs a browser. |
| Attachment URL extraction | Job intake | A user uploads an attachment that is not itself a resume. | LLM job type attachment_url_ai. |
| Job page extraction | Extraction | A pending JobExtraction from a URL. | The employer career site or its public job API. Chromium via Playwright for pages that need a browser. No LLM in the fetch itself. |
| Job encoding | Match | A successful extraction, or pasted text. | Local model sentence-transformers/all-MiniLM-L6-v2. Not OpenAI. CUDA in the encoding worker when available. |
| Profile encoding | Match | Profile save, onboarding, or an admin backfill. | Local MiniLM. No LLM. |
| Free match score | Match | Both JobEncoding and UserEncoding exist and share a model version. | Local vectors and a local cross-encoder. No OpenAI on the default score path. |
| LLM match quality check | Match | A free score already exists. Mode is on re-run, or also for strong new matches. | LLM. Default model match_quality_check_model (gpt-5.6-luna) unless an admin binding overrides it. Forced to the OpenAI-compatible adapter. |
| Score floor, duplicates, applied companies | Match | A saved match score. | Postgres only. |
| Auto-score on visit | Match | Preferences, score new jobs automatically, is on (default for new accounts). | Same as free match: local embeddings. No LLM unless quality check is also on. |
| Save analyzed job | Match | analyze_job_match returned a result. | Redis lock and pubsub. Postgres write. |
| Tailor resume to a job | Tailoring | Extraction, encodings, and a score exist. The job is not hidden. The user did not choose original-resume mode. | LLM job type resume_tailoring. Default OpenAI gpt-5.6-luna. Admin binding can point this job at Anthropic or Gemini. Local checks after the model returns. No vector search inside the write, except the advisory requirement match uses local embeddings. |
| Cover letter | Tailoring | The same tailor run. Always included for a job prepare. Optional in the assistant. | Same LLM client and job type resume_tailoring as the resume call. Different prompt. |
| Project description repair | Tailoring | A tailored resume draft failed the project_description check. | LLM, same resume_tailoring job type, smaller token budget. |
| Resume and cover letter files | Tailoring | tailored_resume_data and optional cover_letter_data are saved. | None. Local document generation. |
| Resume studio | Tailoring | A user on /app/studio. | None. |
| Documents library | Workspace | At least one completed tailor or an assistant save into the library. | None. |
| Jobs dashboard | Workspace | Saved jobs with or without scores. | Your API and Redis pubsub. No model until you trigger score, tailor, or AI search. |
| Natural language job search | Workspace | A search box on Jobs or the scraper admin. | LLM for the filter parse. The search itself is SQL, not a vector index. |
| Home | Workspace | A session. | Postgres only. |
| Insights | Workspace | Jobs have been saved and scored. | Postgres only. |
| Preferences | Workspace | A user record. | Saving a key does not call the provider until the next LLM job. A score-floor change runs a SQL reconcile. |
| Mailbox connection | Interviews | The user connects a mailbox on Integrations. | Nylas API (the mailbox provider behind it: Gmail or similar). |
| Interview pipeline | Interviews | Mail sync, or a manual stage change. Applied jobs can seed a process. | Nylas for the mail. LLM job type interview_mail for classification. |
| Shared reports | Interviews | An interview report the owner chose to share. | None. |
| Assistant chat | Assistant | A session on /app/assistant. | LLM for the chat and the agent. Tailor then uses resume_tailoring. Job search tool uses SQL plus optional job_ai_search. |
| Browser extension | Integrations | The user opens /extension/connect and the extension points at this API (default host nao.it.com). | LLM job type extension_autofill. The page itself is the employer site, not called by our server. |
| Google Sheets auto-post | Integrations | A saved score and a Sheets config (spreadsheet id, service account). | Google Sheets API and Drive readonly, via a service account JSON. |
| Pumble auto-post | Integrations | A Pumble API key, channel, and threshold saved on Integrations. | Pumble HTTP API. |
| Credits and packages | Plans and team | Signup grants 50 credits. Further packs come from an admin grant or a gift. | None. No payment provider is wired. |
| Team space | Plans and team | The owner redeemed a TEAM package. | None. |
| Jobs pipeline admin | Admin | An admin session. Applicants are redirected away from /admin. | Redis and Postgres. Board APIs only when a sync or spider is started. |
| Data management | Admin | Admin session. | Reads Postgres. Does not call OpenAI to render the page. |
| Users admin | Admin | Pending or active users. | None. |
| LLM settings, keys, bindings, benchmark | Admin | Server env keys and the system settings table. | OpenAI, Anthropic, Gemini, or an OpenAI-compatible host such as a future DeepSeek base URL. The binding chooses which one. |
| Match engine admin | Admin | Encodings may be on an old model version. | Local MiniLM and the local cross-encoder. No LLM. |
| Logs | Admin | log_sink has been writing rows. | Postgres. |
| API, workers, data stores | Runtime | Docker Postgres and Redis, then supervisord programs. | Postgres, Redis, and whatever provider keys are configured. Embeddings stay on the encoding worker. |

## Each feature

### Account

#### Landing, privacy, terms

Public pages that stay public even when you are signed in.

- **Before:** Nothing. These routes do not require a session.
- **Depends on:** The React router in App.tsx. No worker and no model.
- **After:** Sign-in, onboarding, or the workspace.
- **Code:** `frontend/src/App.tsx, LandingPage, PrivacyPolicyPage, TermsOfServicePage`
- **External service:** None. Static frontend.

Process:

1. Browser loads /, /privacy-policy, or /terms.
2. App.tsx keeps these routes outside the authenticated shell so a shared link never drops into the workspace.
3. No API call is required to read them.

#### Password login and session

Email and password sign-in, cookie session, logout.

- **Before:** An approved account with a password hash.
- **Depends on:** Users table, AUTH_SECRET_KEY, token denylist.
- **After:** Onboarding if the profile is empty, otherwise Home.
- **Code:** `app/services/auth_service.py, app/services/session_auth.py, app/services/token_denylist.py`
- **External service:** None. Postgres stores the user. Redis holds the denylist when configured.

Process:

1. The login form posts email and password.
2. auth_service checks the password hash and issues a signed token.
3. The token is stored as a cookie. Later requests call get_current_user.
4. Logout puts the token on the denylist so it cannot be reused.

#### Google sign-in

OAuth login beside the password form.

- **Before:** Google OAuth client id and secret in server config.
- **Depends on:** The user row matched by Google email.
- **After:** Same as password login: onboarding, or Home.
- **Code:** `app/services/auth_service.py, config google_oauth_client_id / google_oauth_client_secret`
- **External service:** Google OAuth.

Process:

1. The browser starts the Google OAuth redirect.
2. Google returns to google_oauth_redirect_uri.
3. The API creates or finds the user and issues the same session cookie.

#### Onboarding

First-run profile capture before the workspace is useful.

- **Before:** Approved login with an empty profile.
- **Depends on:** Profile fields and the resume parser if a file is uploaded.
- **After:** Profile save, then a user encoding job so matching can score.
- **Code:** `frontend/src/features/onboarding/OnboardingPage.tsx, encode_user_task`
- **External service:** Resume upload uses the resume_parse LLM job. Encoding uses the local MiniLM model.

Process:

1. Route /onboarding renders OnboardingPage. Admins are sent to /admin instead.
2. The person enters experience or uploads a resume.
3. Saving the profile calls the same profile write as the Profile page and enqueues encode_user.

### Profile

#### Profile editor

The source of truth for name, work history, education, skills, and preferences stored on the user.

- **Before:** A signed-in approved user.
- **Depends on:** Users table columns for profile text, work experience, education, address.
- **After:** User encoding is refreshed. Later match, tailor, and autofill read this profile.
- **Code:** `frontend/src/features/profile/ProfilePage.tsx, app/utils/profile_converter.py, encode_user_task`
- **External service:** None for a manual edit. Encoding is local.

Process:

1. ProfilePage loads the user record.
2. Edits save through the profile API.
3. A profile change enqueues encode_user so vector scores use the new text.

#### Resume upload parse

Turns an uploaded resume file into structured profile fields.

- **Before:** A PDF or document on the profile or onboarding screen.
- **Depends on:** Text extraction from the file, then the LLM.
- **After:** Parsed work, education, and skills land on the profile, then user encoding runs.
- **Code:** `app/services/resume_parse_service.py, app/services/attachment_text_extract.py`
- **External service:** LLM via get_llm_client_for_user, job type resume_parse. Default provider OpenAI, model from the job binding or openai_model.

Process:

1. The file bytes are read to plain text.
2. resume_parse_service sends that text to the LLM with job type resume_parse.
3. The JSON is mapped onto profile fields (titles, dates, skills, location).
4. The profile save triggers encode_user.

#### Project source documents

Portfolio or project files kept as evidence for tailoring, not as the resume itself.

- **Before:** Completed uploads on the profile.
- **Depends on:** Profile source document repository.
- **After:** Tailoring can build a job-specific evidence pack from these docs.
- **Code:** `app/services/profile_source_document_service.py, app/services/profile_evidence_service.py`
- **External service:** Two LLM jobs: profile_source_doc, then later profile_evidence. No vector search in this step.

Process:

1. Upload is stored and marked for extraction.
2. profile_source_document_service calls the LLM with job type profile_source_doc.
3. Structured facts are saved per document.
4. At tailor time, profile_evidence_service (job type profile_evidence) picks the facts that match the posting.

#### Original resume file

The file you send unchanged when application resume source is the original resume.

- **Before:** Preferences, Matching, Resume for applications is set to the original file.
- **Depends on:** original_resume_service and job_pipeline_mode.user_uses_original_resume.
- **After:** Job prepare writes only a cover letter. The uploaded file is what applications use.
- **Code:** `app/services/original_resume_service.py, app/services/job_pipeline_mode.py, run_tailored_content_generation`
- **External service:** Cover letter LLM call only (job type resume_tailoring). No resume-rewrite prompt.

Process:

1. The file is stored for the user.
2. When tailoring runs, cover_only is true.
3. generate_tailored_content_phase_b is called with include_resume false.
4. The cover letter prompt still sees the original resume text prepended to the profile.

### Job intake

#### Paste a job URL

Adds one posting by link and starts extraction.

- **Before:** Signed-in user. Pipeline mode in Preferences decides how far the job runs.
- **Depends on:** URL canonicalizer, blocked-domain list, LinkedIn skip rule.
- **After:** extract_job on the extraction queue.
- **Code:** `app/services/url_manager.py, app/services/blocked_domains_service.py, app/tasks/worker.py extract_job`
- **External service:** None until extraction. The page fetch happens in the next feature.

Process:

1. The Jobs page or assistant submits the URL.
2. url_manager canonicalizes it and blocked_domains_service may reject it.
3. A Job and JobExtraction row are created.
4. extract_job is enqueued on queue job_extraction.

#### Paste a job description

Adds a posting from text when there is no URL to fetch.

- **Before:** Raw description text from the user or the assistant.
- **Depends on:** manual_jd and pasted_job_scoring.
- **After:** Encoding, then free-engine scoring. Tailoring if the pipeline mode allows it.
- **Code:** `app/services/manual_jd.py, app/services/pasted_job_scoring.py, score_pasted_job_task`
- **External service:** Local embeddings (MiniLM). LLM only if a later tailor or quality check is requested.

Process:

1. The text is stored as the job body. No browser fetch.
2. score_pasted_job_task encodes the text and scores it against the user encoding.
3. The job appears on the dashboard with a match score.

#### Saved job sources and site connections

Recurring pulls from boards the user connected.

- **Before:** A source or site connection saved under Integrations or admin job sync.
- **Depends on:** Scheduler cron plus per-source workers.
- **After:** New URLs enter the same extract queue as a pasted link.
- **Code:** `app/services/job_source_sync.py, app/services/job_site_connection_sync.py, app/job_sites/plugins/*`
- **External service:** Board APIs: Indeed via RapidAPI, Adzuna, Welcome to the Jungle Algolia, Remote Rocketship, Jobright, JSearch, Fantastic Jobs, Jobicy, Glassdoor, LinkedIn scraper plugin.

Process:

1. check_job_sync_schedule_task decides what is due.
2. sync_user_job_sources_task and sync_user_job_site_connections_task run the plugins.
3. Plugins return job URLs and snippets.
4. New URLs are promoted into Job rows and extraction is enqueued.

#### Admin scraper spiders

Crawl runs that fill the shared scraped-job pool.

- **Before:** An admin starts a spider or the schedule fires.
- **Depends on:** Scraper worker queue job_scraper_crawl.
- **After:** scrape_promoter copies scraped rows into user-visible jobs, then extraction.
- **Code:** `app/tasks/worker.py run_scraper_task, app/scraper/spiders/*, app/services/scrape_promoter.py`
- **External service:** Those job boards over HTTP. Playwright is used when a spider or extractor needs a browser.

Process:

1. run_scraper_task starts one or more Scrapy spiders.
2. Spiders: Adzuna, Jobright, Remote Rocketship, Welcome to the Jungle, ZipRecruiter.
3. Rows land in the scraper database.
4. Promotion creates platform jobs and can enqueue extraction.

#### Attachment URL extraction

Pulls job links out of an uploaded file (a spreadsheet or a list).

- **Before:** A user uploads an attachment that is not itself a resume.
- **Depends on:** attachment_text_extract, then the LLM if the list is messy.
- **After:** Each found URL enters paste-URL intake.
- **Code:** `app/services/attachment_job_url_ai.py, app/services/attachment_text_extract.py`
- **External service:** LLM job type attachment_url_ai.

Process:

1. The file is converted to text.
2. attachment_job_url_ai asks the model for URLs (job type attachment_url_ai).
3. Each URL is submitted through the normal add-job path.

### Extraction

#### Job page extraction

Fetches a posting and stores title, company, description, requirements, and work mode.

- **Before:** A pending JobExtraction from a URL.
- **Depends on:** Extractor chain chosen by api_detector and the host.
- **After:** encode_job, then analysis if pipeline mode is match or full.
- **Code:** `app/tasks/worker.py extract_job, app/services/extraction_service.py, app/extractors/*`
- **External service:** The employer career site or its public job API. Chromium via Playwright for pages that need a browser. No LLM in the fetch itself.

Process:

1. extract_job loads the URL.
2. LinkedIn URLs can be skipped by _skip_linkedin_extraction.
3. A structured API extractor runs when the host is known: Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Workday, Oracle HCM, Welcome to the Jungle.
4. Otherwise embedded JSON, raw HTML, or the Playwright browser extractor.
5. job_content_cleaner, validator, work_mode_classifier, and security_clearance_detector normalize the text.
6. extraction_cache can reuse a recent fetch of the same URL.
7. On success, encode_job is enqueued. On failure, the job is marked failed for that user.

### Match

#### Job encoding

Turns a posting into vectors and a cross-encoder digest.

- **Before:** A successful extraction, or pasted text.
- **Depends on:** Encoding worker queue job_encoding. GPU when embedding_device is cuda.
- **After:** Analysis scoring, or a deferred then-hook (save, tailor).
- **Code:** `app/services/encoding_service.py, app/services/metadata_vector_extractor.py, encode_job_task`
- **External service:** Local model sentence-transformers/all-MiniLM-L6-v2. Not OpenAI. CUDA in the encoding worker when available.

Process:

1. encode_job_task calls encoding_service.
2. SentenceTransformer all-MiniLM-L6-v2 embeds title, skills, chunks, and domain text.
3. metadata_vector_extractor adds structured fields.
4. A JobEncoding row stores vectors plus ce_text for the cross-encoder.
5. _run_after_encode continues to analysis when the pipeline asked for it.

#### Profile encoding

The same embedding step for the candidate, so a job vector has something to compare.

- **Before:** Profile save, onboarding, or an admin backfill.
- **Depends on:** User profile text, work experience, education, skills, preference text.
- **After:** Every later score_pair for this user uses the new vectors.
- **Code:** `app/services/encoding_service.py build_user_encoding, encode_user_task, backfill_encodings_task`
- **External service:** Local MiniLM. No LLM.

Process:

1. encode_user_task builds a UserEncoding.
2. The same MiniLM model embeds profile fields.
3. ce_text is the compact digest the cross-encoder reads beside the job digest.
4. backfill_encodings_task rebuilds rows when the model version changes.

#### Free match score

Scores a job against the profile without a writing model. This is the default score on the dashboard.

- **Before:** Both JobEncoding and UserEncoding exist and share a model version.
- **Depends on:** vector_match_service score_pair_v5 and, when weights exist, the cross-encoder.
- **After:** Save onto the job row. Optional LLM quality check. Optional tailor. Optional Sheets or Pumble post.
- **Code:** `app/services/vector_match_service.py, app/services/vector_match_v5.py, app/services/cross_encoder.py, analyze_job_match`
- **External service:** Local vectors and a local cross-encoder. No OpenAI on the default score path.

Process:

1. analyze_job_match loads both encodings.
2. Cosine features cover skills, title, chunks, years, and level.
3. Tree models in vector_match_v5 turn features into six dimension scores.
4. The cross-encoder (nao-match-ce-v5) reads the two digests together and predicts the same dimensions plus a real-posting logit. If CUDA or the weights are missing, the tree scores stand alone.
5. MATCH_DIMENSION_WEIGHTS blend the dimensions into one overall score.
6. Work mode, country, and security clearance can zero or skip a job before it is shown.
7. The result is handed to save_analyzed_job.

#### LLM match quality check

A second opinion on the free score, only when the user opts in.

- **Before:** A free score already exists. Mode is on re-run, or also for strong new matches.
- **Depends on:** Preferences, Matching, AI quality check.
- **After:** The checked score can replace or annotate the free score. It does not write the resume.
- **Code:** `app/services/match_quality_check.py, quality_check_job_match`
- **External service:** LLM. Default model match_quality_check_model (gpt-5.6-luna) unless an admin binding overrides it. Forced to the OpenAI-compatible adapter.

Process:

1. quality_check_job_match is enqueued on the analysis queue.
2. match_quality_check sends profile and job to the LLM with job type match_quality_check.
3. The model returns dimension scores. A daily cap can stop further calls.
4. The job row is updated. Tailoring is a separate later step.

#### Score floor, duplicates, applied companies

Hides jobs after scoring so the dashboard stays usable.

- **Before:** A saved match score.
- **Depends on:** Preferences: minimum match score, duplicate handling, hide applied companies, score comparison.
- **After:** Hidden jobs stay in the database but leave the default list. Tailoring is skipped for hidden jobs.
- **Code:** `app/services/min_match_score_reconcile.py, app/services/post_analysis_dedup.py, app/services/dedup_rules_reconcile.py`
- **External service:** Postgres only.

Process:

1. min_match_score_reconcile hides or restores jobs against the floor.
2. post_analysis_dedup compares company and score with jobs already on the list.
3. An applied company can hide later postings from that company.
4. Score comparison keeps the stronger of two near-duplicate postings.
5. Changing a setting previews how many jobs would hide or return, then reconciles.

#### Auto-score on visit

Catches up unscored visible jobs when you open Jobs.

- **Before:** Preferences, score new jobs automatically, is on (default for new accounts).
- **Depends on:** auto_prepare_service and the visit cap.
- **After:** Those jobs enter analyze_job_match. Documents are a separate switch.
- **Code:** `app/services/auto_prepare_service.py, app/services/scored_ready_service.py`
- **External service:** Same as free match: local embeddings. No LLM unless quality check is also on.

Process:

1. Opening Jobs asks for unscored visible jobs.
2. At most auto_score_on_visit_limit jobs per visit, with a cooldown.
3. Each job is enqueued for encoding or analysis if extraction already finished.

#### Save analyzed job

Writes the score onto the user's job and fans out to tailor and auto-post.

- **Before:** analyze_job_match returned a result.
- **Depends on:** Per-user save lock so two scores for one person do not clobber each other.
- **After:** Dashboard row updates over the websocket. Tailor queue and autopost queue may start.
- **Code:** `app/tasks/worker.py save_analyzed_job, _after_save, app/api/websocket.py`
- **External service:** Redis lock and pubsub. Postgres write.

Process:

1. save_analyzed_job takes a Redis lock for that user.
2. _save_one writes the match.
3. _after_save enqueues tailoring when pipeline mode is full and auto-prepare documents is on.
4. _enqueue_or_run_auto_posts hands Sheets and Pumble to the autopost queue.
5. publish_ws_event tells the open Jobs page to refresh.

### Tailoring

#### Tailor resume to a job

Writes the application resume JSON for one posting. Default strategy is Rebuild around the job.

- **Before:** Extraction, encodings, and a score exist. The job is not hidden. The user did not choose original-resume mode.
- **Depends on:** User strategy (job_first or evidence), custom prompt if set, career facts or the evidence map.
- **After:** Project-description repair if needed, then the resume file build.
- **Code:** `app/services/job_match_orchestrator.py run_tailored_content_generation, app/services/job_match_service.py generate_tailored_content_phase_b, app/services/resume_tailoring.py, app/prompts/resume_tailoring_prompt.py, app/prompts/job_match_phase_b_prompt.py`
- **External service:** LLM job type resume_tailoring. Default OpenAI gpt-5.6-luna. Admin binding can point this job at Anthropic or Gemini. Local checks after the model returns. No vector search inside the write, except the advisory requirement match uses local embeddings.

Process:

1. generate_tailored_content on queue job_tailoring calls run_tailored_content_generation.
2. Hidden and already-applied jobs are skipped unless the run is manual.
3. An evidence pack is built from source documents (LLM job profile_evidence) when docs exist.
4. job_first: build_tailoring_plan fills career facts and target stack, then the model answers TAILORING_USER_TEMPLATE. Employers and dates are restored in finalize_tailored_resume. Up to two retries.
5. evidence: the Phase B prompt and JOB_MATCH_PHASE_B_USER_TEMPLATE are used instead. Skills the profile never states stay out.
6. Both paths use job type resume_tailoring, temperature 0.4.

#### Cover letter

A separate model call that writes only the letter body.

- **Before:** The same tailor run. Always included for a job prepare. Optional in the assistant.
- **Depends on:** cover_letter_prompt.py. Original profile text, not the rewritten resume, on the job_first path.
- **After:** Stored beside the resume JSON. The file build renders it.
- **Code:** `app/prompts/cover_letter_prompt.py, _cover_call in job_match_service.py`
- **External service:** Same LLM client and job type resume_tailoring as the resume call. Different prompt.

Process:

1. COVER_LETTER_SYSTEM_PROMPT plus COVER_LETTER_USER_TEMPLATE are sent.
2. The model returns JSON with cover_letter.body: greeting, 3 to 4 paragraphs, sign-off.
3. A failed letter is retried once.
4. Original-resume mode still writes the letter and skips the resume rewrite.

#### Project description repair

A short follow-up call when a role blurb does not introduce its bullets.

- **Before:** A tailored resume draft failed the project_description check.
- **Depends on:** PROJECT_DESCRIPTION_SYSTEM_PROMPT. Bullets are already final.
- **After:** The resume JSON is saved and the document build starts.
- **Code:** `app/services/job_match_service.py _repair_project_descriptions`
- **External service:** LLM, same resume_tailoring job type, smaller token budget.

Process:

1. project_description_problems lists the bad roles.
2. Only those roles, the job text, and posting skills are sent.
3. The model returns a new sentence or two per role.
4. apply_description_repairs writes them in place.

#### Resume and cover letter files

Renders the JSON into DOCX and PDF using the user's template.

- **Before:** tailored_resume_data and optional cover_letter_data are saved.
- **Depends on:** Resume template, theme, and filename pattern.
- **After:** Files show on Documents and can be downloaded or autofilled.
- **Code:** `app/services/resume_build_orchestrator.py, app/services/document_renderer.py, app/services/resume_blueprint_renderer.py, build_resume_task`
- **External service:** None. Local document generation.

Process:

1. _enqueue_resume_doc_build puts build_resume_task on queue resume_build.
2. resume_build_orchestrator fills the template from the JSON.
3. document_renderer and the design compilers produce DOCX and PDF.
4. A websocket event marks the document ready.

#### Resume studio

Visual template, theme, and section layout for the files above.

- **Before:** A user on /app/studio.
- **Depends on:** resume_design_service, themes, custom themes, cover letter design compiler.
- **After:** The next document build uses the saved design. It does not by itself call the tailor prompt.
- **Code:** `frontend/src/features/studio/ResumeStudioPage.tsx, app/services/resume_design_service.py, app/services/resume_design_compiler.py, app/services/resume_themes.py`
- **External service:** None.

Process:

1. ResumeStudioPage edits sections, order, and theme.
2. resume_design_compiler turns the design into render instructions.
3. cover_letter_design_compiler does the same for the letter.
4. Saving does not rescore jobs. Rebuild a document to see the new layout.

### Workspace

#### Documents library

Lists tailored resumes, cover letters, and the job each one was written for.

- **Before:** At least one completed tailor or an assistant save into the library.
- **Depends on:** Resume build rows and the library save from the agent.
- **After:** Download, preview, delete. The assistant can add a resume here without a dashboard job.
- **Code:** `frontend/src/features/documents/DocumentsPage.tsx, app/api/document_routes.py, save_ai_tailored_as_library_resume`
- **External service:** None.

Process:

1. DocumentsPage loads resume rows and file states.
2. Preview uses the PDF embed. Download uses the built file.
3. A row links back to the job description used for that tailor.

#### Jobs dashboard

The table of postings: filters, sort, hide, applied, and live updates.

- **Before:** Saved jobs with or without scores.
- **Depends on:** Job list API, websocket events, preference filters.
- **After:** Manual tailor, re-score, apply, or open the job.
- **Code:** `frontend/src/features/jobs/JobsPage.tsx, app/api/routes.py job list endpoints, app/api/websocket.py`
- **External service:** Your API and Redis pubsub. No model until you trigger score, tailor, or AI search.

Process:

1. JobsPage loads the current view tab and filters (remote, title, company, source, keywords).
2. Scores, strengths, and gaps come from the saved match, not a fresh LLM call.
3. Mark applied, hide, or restore writes user job status.
4. Websocket events from save, tailor, and document build refresh the row in place.

#### Natural language job search

Turns a sentence into filters over jobs you already have, or over the scrape pool.

- **Before:** A search box on Jobs or the scraper admin.
- **Depends on:** job_ai_search_service or scraper_ai_search_service.
- **After:** The table shows the filtered set. It does not add new jobs by itself.
- **Code:** `app/services/job_ai_search_service.py, app/services/scraper_ai_search_service.py`
- **External service:** LLM for the filter parse. The search itself is SQL, not a vector index.

Process:

1. The sentence goes to the LLM (job type job_ai_search or scraper_ai_search).
2. The model returns a filter object: keywords, remote, salary, job type.
3. SQL applies that filter to saved jobs or scraped rows.

#### Home

Start page with counts and the composer entry.

- **Before:** A session.
- **Depends on:** dashboard_stats and weekly_progress.
- **After:** Jumps into Jobs, assistant, or add-job.
- **Code:** `frontend/src/features/home/HomePage.tsx, app/services/dashboard_stats.py, app/services/weekly_progress.py`
- **External service:** Postgres only.

Process:

1. HomePage loads counts for the signed-in user.
2. Numbers are aggregates of jobs, scores, and applications already stored.

#### Insights

Charts of the pipeline: scores, sources, and progress over time.

- **Before:** Jobs have been saved and scored.
- **Depends on:** The analysis API behind /app/analysis.
- **After:** Read only. Changing a chart does not rescore.
- **Code:** `frontend/src/features/insights/InsightsPage.tsx, app/services/dashboard_stats.py`
- **External service:** Postgres only.

Process:

1. InsightsPage requests aggregate series.
2. dashboard_stats and related queries group match scores, statuses, and time.

#### Preferences

The switches that change intake, scoring, tailoring, and prompts.

- **Before:** A user record.
- **Depends on:** User settings columns.
- **After:** The next job run obeys the new mode. Some toggles reconcile existing rows immediately.
- **Code:** `frontend/src/features/settings/PreferencesPage.tsx and the tab components, app/storage/user_repository.py`
- **External service:** Saving a key does not call the provider until the next LLM job. A score-floor change runs a SQL reconcile.

Process:

1. Job search: countries, work mode, what happens when you add a job (extract only, up to analysis, or full pipeline), free-text match preferences.
2. Matching: minimum score, duplicate rules, original vs tailored resume, auto-score, auto-prepare documents, paste-link behavior, LLM quality check.
3. Application details: address and EEO answers used by the extension autofill.
4. AI and keys: personal provider key and dashboard model.
5. Prompts: custom resume instructions and custom cover letter instructions.

### Interviews

#### Mailbox connection

Reads hiring email through Nylas so interviews can be built from the inbox.

- **Before:** The user connects a mailbox on Integrations.
- **Depends on:** nylas_service and a MailConnection row.
- **After:** Sync creates interview events. Verification-code lookup can also read this grant.
- **Code:** `app/services/nylas_service.py, app/api/mail_routes.py`
- **External service:** Nylas API (the mailbox provider behind it: Gmail or similar).

Process:

1. OAuth or API key connects the mailbox and stores a Nylas grant id.
2. Sync lists messages after a cursor.
3. Bodies are converted from HTML to text.

#### Interview pipeline

One process per company and role. Email moves the stage forward. The user can override.

- **Before:** Mail sync, or a manual stage change. Applied jobs can seed a process.
- **Depends on:** interview_extraction to classify each email.
- **After:** Interviews page, weekly progress, shareable report.
- **Code:** `app/services/interview_service.py, app/services/interview_extraction.py, app/services/mail_applications.py, InterviewsPage`
- **External service:** Nylas for the mail. LLM job type interview_mail for classification.

Process:

1. New messages are classified by the LLM (job type interview_mail) into kinds such as recruiter screen, assessment, offer, rejection.
2. KIND_STAGE maps the kind onto applied, screening, assessment, interviewing, final, or offer.
3. Email only moves a stage forward. A rejection closes the process.
4. The user can set any stage from InterviewsPage.
5. Report preview and share links read the same process list.

#### Shared reports

A read-only link to an interview report, plus a list of reports shared with you.

- **Before:** An interview report the owner chose to share.
- **Depends on:** report_share service.
- **After:** Recipient opens /app/shared/:shareId. No tailor or score runs.
- **Code:** `app/services/report_share.py, app/api/report_share_routes.py, SharedReportPage`
- **External service:** None.

Process:

1. The owner creates a share.
2. SharedWithMePage lists incoming shares.
3. SharedReportPage renders the report for that share id.

### Assistant

#### Assistant chat

Streaming chat that can call tools: tailor, filter the jobs table, search, sync, mark applied.

- **Before:** A session on /app/assistant.
- **Depends on:** Agent orchestrator and the tool catalog.
- **After:** Tool results refresh Jobs or Documents. A tailor here uses the same Phase B prompts.
- **Code:** `app/api/assistant_routes.py, app/services/agent/orchestrator.py, app/services/agent/catalog.py, app/services/resume_ai_chat_service.py`
- **External service:** LLM for the chat and the agent. Tailor then uses resume_tailoring. Job search tool uses SQL plus optional job_ai_search.

Process:

1. The user message is streamed with job type assistant_chat.
2. The agent loop (job type agent) picks a tool.
3. tailor_resume runs the resume AI pipeline and saves a library document. Cover letter only if asked.
4. update_dashboard changes the Jobs table filters in the main window.
5. search_jobs, get_job_details, submit_job, set_applied, rerun_matches, trigger_sync, get_stats, get_sync_status call the same services as the pages.

### Integrations

#### Browser extension

Side panel on the career site: home snapshot, connect, autofill, quick apply.

- **Before:** The user opens /extension/connect and the extension points at this API (default host nao.it.com).
- **Depends on:** Extension routes, application details, and the current job if one is open.
- **After:** An application session can be marked in progress. Autofill types profile answers into the form.
- **Code:** `extension/, app/api/extension_routes.py, app/api/assistant_routes.py autofill handlers, app/services/quick_apply.py`
- **External service:** LLM job type extension_autofill. The page itself is the employer site, not called by our server.

Process:

1. GET /extension/home returns counts, weekly progress, and in-progress sessions in one call.
2. Autofill (job type extension_autofill) maps form fields to profile, address, and EEO answers.
3. quick_apply can draft from the resume AI path when the form needs a written answer.

#### Google Sheets auto-post

Appends a job row to the user's spreadsheet after a score clears their filters.

- **Before:** A saved score and a Sheets config (spreadsheet id, service account).
- **Depends on:** Autopost queue, auto_post_filters, minimum score.
- **After:** The sheet gains a row. The job on the dashboard is unchanged.
- **Code:** `app/services/google_sheets_service.py, app/services/auto_post_filters.py, run_match_auto_posts_task`
- **External service:** Google Sheets API and Drive readonly, via a service account JSON.

Process:

1. save finishes and enqueues run_match_auto_posts_task.
2. The score and dashboard filters are checked.
3. google_sheets_service appends the URL and fields to the configured tab.
4. A URL already present is not written again.

#### Pumble auto-post

Posts a matching job into a Pumble channel.

- **Before:** A Pumble API key, channel, and threshold saved on Integrations.
- **Depends on:** The same autopost task as Sheets.
- **After:** A chat message. Independent of Sheets.
- **Code:** `app/services/pumble_service.py, run_match_auto_posts_task`
- **External service:** Pumble HTTP API.

Process:

1. After save, the autopost worker loads Pumble configs for the user.
2. If the score passes the threshold and filters, pumble_service posts to the channel.
3. The integration can be disabled without deleting the key.

### Plans and team

#### Credits and packages

Credit balance and held packages. Payments are not live. Admins grant packages.

- **Before:** Signup grants 50 credits. Further packs come from an admin grant or a gift.
- **Depends on:** store_service and the packages admin page.
- **After:** Redeeming a credit pack adds balance. Redeeming TEAM creates a team space.
- **Code:** `app/services/store_service.py, frontend/src/features/plans/PlansPage.tsx, AdminPackagesPage`
- **External service:** None. No payment provider is wired.

Process:

1. PlansPage shows balance and held packages.
2. A gift to an unknown email waits until that email signs up.
3. There is no Stripe charge in this path.

#### Team space

A TEAM package becomes one space. Members and a per-member report.

- **Before:** The owner redeemed a TEAM package.
- **Depends on:** team_service.
- **After:** Team page and team member report. Sharing a report is separate.
- **Code:** `app/services/team_service.py, app/api/team_routes.py, TeamPage, TeamMemberReportPage`
- **External service:** None.

Process:

1. Redeem creates a TeamSpace.
2. The owner invites members.
3. TeamMemberReportPage shows that member's pipeline numbers.

### Admin

#### Jobs pipeline admin

Operator view of extraction, sync, and scrape health.

- **Before:** An admin session. Applicants are redirected away from /admin.
- **Depends on:** pipeline_health, scraper run rows, job sync schedule.
- **After:** Start or inspect sync and scrape. Does not tailor on behalf of a user by itself.
- **Code:** `frontend/src/features/admin/pipeline/AdminPipelinePage.tsx, app/services/pipeline_health.py, JobSyncTab, WorkersTab`
- **External service:** Redis and Postgres. Board APIs only when a sync or spider is started.

Process:

1. AdminPipelinePage loads queue and scrape status.
2. Job sync tab edits schedules and runs sync_user_job_sources.
3. Workers tab shows Redis queue depth and database connectivity.

#### Data management

Usage, activity, and cleanup across users and jobs.

- **Before:** Admin session.
- **Depends on:** data_management_routes and the stats services.
- **After:** Deletes or repairs rows. Match backfill can be started from the match engine tab.
- **Code:** `app/api/data_management_routes.py, app/services/data_management_usage.py, app/services/llm_usage.py, app/services/data_management_ops.py`
- **External service:** Reads Postgres. Does not call OpenAI to render the page.

Process:

1. AdminDataPage shows token use by feature, including resume_tailoring.
2. llm_usage rows are written by every LLM call label.
3. Cleanup operations live in data_management_ops.

#### Users admin

Inspect accounts, change roles, disable or enable an account, and reset a password.

- **Before:** A signed-in admin.
- **Depends on:** The users table. Disabling an account sets is_active false and blocks sign-in.
- **After:** A disabled account cannot sign in. Signup itself does not wait for approval.
- **Code:** `frontend/src/features/admin/users/AdminUsersPage.tsx`
- **External service:** None.

Process:

1. AdminUsersPage lists accounts.
2. An admin promotes, demotes, enables, disables, or deletes an account.
3. A password reset signs that user out everywhere.

#### LLM settings, keys, bindings, benchmark

Which provider and model each platform job uses.

- **Before:** Server env keys and the system settings table.
- **Depends on:** llm_provider_keys_service, system_settings_service, model discovery.
- **After:** The next LLM call for that job type uses the binding. Tailor prompts do not change.
- **Code:** `frontend/src/features/admin/system/LlmTab.tsx, KeysTab, BenchmarkTab, app/services/llm_provider_keys_service.py, app/core/llm_client.py`
- **External service:** OpenAI, Anthropic, Gemini, or an OpenAI-compatible host such as a future DeepSeek base URL. The binding chooses which one.

Process:

1. Keys tab stores encrypted provider keys (OpenAI, Anthropic, Gemini).
2. A job binding maps a job type (resume_tailoring, job_analysis, and the others) to a key and a model.
3. openai_api_base, when set, sends the OpenAI adapter to a compatible host.
4. Benchmark tab runs llm_benchmark against the configured models.
5. Model discovery lists models from GET {base}/models.

#### Match engine admin

Backfill encodings and diagnose one job and user pair.

- **Before:** Encodings may be on an old model version.
- **Depends on:** encoding backfill and match_diagnose_service.
- **After:** New vectors. Existing scores update when those jobs are rescored.
- **Code:** `frontend/src/features/admin/system/MatchEngineTab.tsx, app/services/match_diagnose_service.py, backfill_encodings_task`
- **External service:** Local MiniLM and the local cross-encoder. No LLM.

Process:

1. Backfill enqueues backfill_encodings_task.
2. Diagnose loads one job id and prints dimension features, weights, and timing.
3. This page does not call the tailor prompt.

#### Logs

Structured events from API and workers, with a purge cron.

- **Before:** log_sink has been writing rows.
- **Depends on:** logs_routes and the log table.
- **After:** purge_old_logs_task deletes old rows on a schedule.
- **Code:** `app/services/log_sink.py, app/api/logs_routes.py, purge_old_logs_task, AdminLogsPage`
- **External service:** Postgres.

Process:

1. Workers and the API emit structured logs.
2. AdminLogsPage filters them.
3. The cron task drops rows past the retention window.

### Runtime

#### API, workers, data stores

The process layout everything else runs on.

- **Before:** Docker Postgres and Redis, then supervisord programs.
- **Depends on:** FastAPI, arq, nginx, GitHub Actions deploy to /opt/showerv3.
- **After:** Every feature above is a route on the API or a job on one queue.
- **Code:** `app/tasks/worker.py, app/main entry, deploy/supervisor/nao-wsl.conf, deploy/nginx/`
- **External service:** Postgres, Redis, and whatever provider keys are configured. Embeddings stay on the encoding worker.

Process:

1. nginx serves the SPA and proxies /api to FastAPI. Production host is nao.it.com.
2. Queues: job_extraction, job_encoding, job_analysis, job_save, job_tailoring, resume_build, job_scraper_crawl, job_autopost.
3. Programs: api, extraction, encoding, analysis, save, tailoring, resume, scraper, autopost, vite.
4. Websocket fans worker events to open browsers through Redis pubsub.

