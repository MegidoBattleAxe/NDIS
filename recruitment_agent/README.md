# Multi-Agent Recruitment Workflow

A non-framework, multi-agent hiring pipeline built on the Mistral AI SDK, ported from the
[Mistral cookbook: Multi Agent Workflow For Recruitment](https://docs.mistral.ai/resources/cookbooks/mistral-agents-non_framework-recruitment_agent-multi_agent_workflow_for_recruitment).

Six specialized agents work in sequence:

1. **DocumentAgent** — extracts text from resumes / job descriptions with Mistral OCR
2. **JobAnalysisAgent** — turns the job description into structured `JobRequirements`
3. **ResumeAnalysisAgent** — turns each resume into a structured `CandidateProfile`
4. **MatchingAgent** — scores each candidate against the requirements (0–100)
5. **EmailCommunicationAgent** — sends personalized interview invitations (Gmail SMTP + Calendly link) to candidates above a score threshold
6. **CoordinatorAgent** — orchestrates the whole workflow and writes a ranked `candidate_results.json`

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

- `MISTRAL_API_KEY` — get one at [console.mistral.ai/api-keys](https://console.mistral.ai/api-keys)
- `SENDER_EMAIL` / `APP_PASSWORD` — Gmail address + [app password](https://myaccount.google.com/apppasswords). **Leave `APP_PASSWORD` empty to dry-run**: emails are generated and printed but never sent.
- `CALENDLY_LINK` — scheduling link sent to shortlisted candidates

## Run the workflow

Sample data (a Senior Data Scientist job description + 13 candidate resumes) is bundled in `data/`:

```bash
python main.py \
  --jd data/job_description.pdf \
  --resumes data/resumes \
  --output candidate_results.json \
  --threshold 65 \
  --max-resumes 5
```

Useful flags: `--no-email` (skip email entirely), `--delay` (seconds between API calls, default 10),
`--threshold` (minimum score for an interview invite, default 65).

The run prints a ranked candidate list and writes the full structured results to the output JSON.

## Project layout

```
main.py                    CLI entrypoint (config via env / .env / flags)
recruitment/
  models.py                Pydantic models for structured extraction & scoring
  agents.py                Agent base class + the 5 specialized agents
  coordinator.py           CoordinatorAgent: orchestrates the workflow
tests/test_workflow.py     Offline smoke tests with a mocked Mistral client
data/                      Sample job description + resumes (from the cookbook repo)
```

## Tests

The tests mock the Mistral client, so no API key or network is needed:

```bash
python -m unittest discover -s tests -v
```
