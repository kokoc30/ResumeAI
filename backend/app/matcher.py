"""Semantic matching and explainable scoring helpers."""


def _clamp_score(value: float) -> float:
    """Keep a decimal score inside the expected 0-1 range."""
    return max(0.0, min(1.0, value))


def filter_top_matches(
    matches: list[dict],
    min_similarity: float = 0.35,
    max_results: int = 8,
) -> list[dict]:
    """Filter, deduplicate, and sort semantic resume matches.

    Chroma can return the same resume chunk for several job-side queries. For
    the API response, we keep only the strongest match for each resume chunk and
    return the fields supported by the current ResumeMatch model.
    """
    if not matches or max_results <= 0:
        return []

    cleaned_matches: list[dict] = []
    for match in matches:
        try:
            similarity = float(match.get("similarity_score", 0.0))
        except (TypeError, ValueError):
            similarity = 0.0

        similarity = _clamp_score(similarity)
        if similarity < min_similarity:
            continue

        resume_chunk = str(match.get("resume_chunk", "")).strip()
        job_requirement = str(match.get("job_requirement", "")).strip()
        if not resume_chunk or not job_requirement:
            continue

        cleaned_matches.append(
            {
                "job_requirement": job_requirement,
                "resume_chunk": resume_chunk,
                "similarity_score": round(similarity, 2),
                "chunk_id": match.get("chunk_id"),
            }
        )

    cleaned_matches.sort(key=lambda item: item["similarity_score"], reverse=True)

    deduped: list[dict] = []
    seen_chunks: set[str] = set()
    for match in cleaned_matches:
        chunk_key = str(match.get("chunk_id") or match["resume_chunk"]).strip().lower()
        if chunk_key in seen_chunks:
            continue

        seen_chunks.add(chunk_key)
        deduped.append(
            {
                "job_requirement": match["job_requirement"],
                "resume_chunk": match["resume_chunk"],
                "similarity_score": match["similarity_score"],
            }
        )

        if len(deduped) >= max_results:
            break

    return deduped


def calculate_match_score(
    matched_skill_count: int,
    job_skill_count: int,
    semantic_matches: list[dict],
    resume_chunk_count: int,
    high_priority_missing_count: int = 0,
    high_priority_job_count: int = 0,
    high_priority_matched_count: int = 0,
) -> int:
    """Calculate a simple explainable 0-100 resume/job match score.

    Formula when known job skills are detected:
    - 55% weight on overall skill keyword overlap (matched / total job skills).
    - 35% weight on average semantic similarity from filtered vector matches.
    - + small bonus per matched high-priority specialized skill, capped at 0.20.
      This recognizes substantive matches on the role's most important
      requirements even when the catalog detects many other skills in the JD.
    - − up to 20% penalty when the resume is missing the high-priority skills
      the job description marks as required/specialized.

    When no known job skills are detected, semantic evidence carries most of
    the score because the skill dictionary has no signal for that request.

    The penalty keeps specialized roles (compilers, quantum, kernel/driver,
    etc.) from scoring high just because broad terms overlap.
    """
    safe_matched_skill_count = max(0, matched_skill_count)
    safe_job_skill_count = max(0, job_skill_count)
    safe_resume_chunk_count = max(0, resume_chunk_count)
    safe_high_priority_missing = max(0, high_priority_missing_count)
    safe_high_priority_total = max(0, high_priority_job_count)
    safe_high_priority_matched = max(0, high_priority_matched_count)

    semantic_scores = [
        _clamp_score(float(match.get("similarity_score", 0.0)))
        for match in semantic_matches
        if match.get("similarity_score") is not None
    ]
    semantic_score = (
        sum(semantic_scores) / len(semantic_scores)
        if semantic_scores and safe_resume_chunk_count > 0
        else 0.0
    )

    if safe_job_skill_count > 0:
        skill_score = _clamp_score(safe_matched_skill_count / safe_job_skill_count)
        base_score = (skill_score * 0.55) + (semantic_score * 0.35)

        if safe_high_priority_total > 0:
            high_priority_missing_ratio = _clamp_score(
                safe_high_priority_missing / safe_high_priority_total
            )
        else:
            high_priority_missing_ratio = 0.0

        penalty = high_priority_missing_ratio * 0.20
        bonus = min(0.20, 0.07 * safe_high_priority_matched)
        final_score = base_score + bonus - penalty
    else:
        final_score = semantic_score * 0.85

    return int(round(_clamp_score(final_score) * 100))


def build_summary(
    match_score: int,
    matched_skill_count: int,
    missing_skill_count: int,
    semantic_match_count: int,
) -> str:
    """Build a short user-facing summary for the analysis response."""
    if match_score >= 75:
        level = "strong match"
        guidance = "The resume shows solid alignment with the job description."
    elif match_score >= 50:
        level = "partial match"
        guidance = "The resume has relevant overlap, but some important evidence is missing or could be clearer."
    else:
        level = "low match"
        guidance = "The resume needs stronger targeted evidence for this role."

    return (
        f"This resume looks like a {level} with an estimated score of {match_score}/100. "
        f"Detected {matched_skill_count} matched skill(s), {missing_skill_count} missing skill(s), "
        f"and {semantic_match_count} useful semantic resume match(es). "
        f"{guidance} This estimate is based on detected skills and semantic resume evidence, not a guarantee."
    )
