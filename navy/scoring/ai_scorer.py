from __future__ import annotations

import json
import logging
import re

from navy.config import ScoringConfig
from navy.models import Job, ScoredJob

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a job relevance scorer. Given a candidate profile and a batch of job listings, rate each job's relevance to the candidate from 0.0 to 1.0.

Scoring guidelines:
- 0.9-1.0: Perfect match — role, skills, and seniority align exactly
- 0.7-0.8: Strong match — most skills align, role is very relevant
- 0.5-0.6: Moderate match — some skills overlap, partially relevant role
- 0.3-0.4: Weak match — few overlapping skills or tangentially related
- 0.0-0.2: No match — completely different field or skill set

Respond ONLY with a JSON array. Each element must have:
- "job_id": the linkedin_id string
- "score": float between 0.0 and 1.0
- "reasoning": 1-2 sentence explanation
- "matched_keywords": list of matching skills/terms found in the job"""

BATCH_SIZE = 8


def _build_user_prompt(user_profile: str, jobs: list[Job]) -> str:
    parts = [f"## Candidate Profile\n{user_profile}\n\n## Jobs to Score\n"]
    for i, job in enumerate(jobs):
        desc = (job.description or "No description available")[:600]
        parts.append(
            f"{i + 1}. [ID: {job.linkedin_id}]\n"
            f"   Title: {job.title}\n"
            f"   Company: {job.company_name}\n"
            f"   Location: {job.location}\n"
            f"   Description: {desc}\n"
        )
    return "\n".join(parts)


def _parse_scores(response_text: str, jobs: list[Job]) -> dict[str, dict]:
    json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if not json_match:
        logger.warning("Could not extract JSON array from LLM response")
        return {}

    try:
        scores = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM JSON: {e}")
        return {}

    return {str(s["job_id"]): s for s in scores if "job_id" in s}


def _keyword_fallback_score(job: Job, user_profile: str) -> ScoredJob:
    keywords = [
        "seo", "growth", "ai", "automation", "prompt", "python",
        "low code", "low-code", "machine learning", "llm", "marketing",
        "data", "engineer", "specialist", "lead", "senior",
    ]
    title_lower = job.title.lower()
    desc_lower = (job.description or "").lower()
    company_lower = job.company_name.lower()
    profile_lower = user_profile.lower()

    matched = []
    score = 0.0
    for kw in keywords:
        if kw not in profile_lower:
            continue
        # Title matches are worth 2x
        if kw in title_lower:
            matched.append(kw)
            score += 2.0
        elif kw in desc_lower or kw in company_lower:
            matched.append(kw)
            score += 1.0

    # Normalize: 4 points = 100% (e.g. 2 title matches)
    score = min(score / 4.0, 1.0)

    return ScoredJob(
        job=job,
        relevance_score=round(score, 2),
        score_reasoning="Keyword-based scoring",
        matched_keywords=matched,
    )


def _score_batch_openai(
    jobs: list[Job], user_profile: str, config: ScoringConfig, api_key: str
) -> list[ScoredJob]:
    import openai

    client = openai.OpenAI(api_key=api_key)
    user_prompt = _build_user_prompt(user_profile, jobs)

    try:
        response = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        result_text = response.choices[0].message.content or ""
        scores_map = _parse_scores(result_text, jobs)
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        scores_map = {}

    scored_jobs = []
    for job in jobs:
        if job.linkedin_id in scores_map:
            s = scores_map[job.linkedin_id]
            scored_jobs.append(
                ScoredJob(
                    job=job,
                    relevance_score=float(s.get("score", 0)),
                    score_reasoning=s.get("reasoning", ""),
                    matched_keywords=s.get("matched_keywords", []),
                )
            )
        else:
            scored_jobs.append(_keyword_fallback_score(job, user_profile))

    return scored_jobs


def _score_batch_anthropic(
    jobs: list[Job], user_profile: str, config: ScoringConfig, api_key: str
) -> list[ScoredJob]:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = _build_user_prompt(user_profile, jobs)

    try:
        response = client.messages.create(
            model=config.model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        result_text = response.content[0].text
        scores_map = _parse_scores(result_text, jobs)
    except Exception as e:
        logger.error(f"Anthropic API call failed: {e}")
        scores_map = {}

    scored_jobs = []
    for job in jobs:
        if job.linkedin_id in scores_map:
            s = scores_map[job.linkedin_id]
            scored_jobs.append(
                ScoredJob(
                    job=job,
                    relevance_score=float(s.get("score", 0)),
                    score_reasoning=s.get("reasoning", ""),
                    matched_keywords=s.get("matched_keywords", []),
                )
            )
        else:
            scored_jobs.append(_keyword_fallback_score(job, user_profile))

    return scored_jobs


def score_jobs(
    jobs: list[Job],
    config: ScoringConfig,
    api_key: str,
    dry_run: bool = False,
) -> list[ScoredJob]:
    if not jobs:
        return []

    if dry_run or not api_key:
        if not api_key:
            logger.warning("No API key provided — using keyword fallback scoring")
        else:
            logger.info("Dry run — using keyword fallback scoring")
        return [_keyword_fallback_score(j, config.user_profile) for j in jobs]

    scored: list[ScoredJob] = []

    for i in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[i : i + BATCH_SIZE]
        logger.info(f"Scoring batch {i // BATCH_SIZE + 1} ({len(batch)} jobs)...")

        if config.provider == "anthropic":
            batch_scored = _score_batch_anthropic(
                batch, config.user_profile, config, api_key
            )
        else:
            batch_scored = _score_batch_openai(
                batch, config.user_profile, config, api_key
            )

        scored.extend(batch_scored)

    logger.info(f"Scored {len(scored)} jobs total")
    return scored
