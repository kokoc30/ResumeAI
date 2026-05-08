from app.matcher import build_summary, calculate_match_score, filter_top_matches


def test_filter_top_matches_removes_weak_matches():
    matches = [
        {
            "job_requirement": "Python",
            "resume_chunk": "Built APIs with Python.",
            "similarity_score": 0.62,
            "chunk_id": "chunk_0",
        },
        {
            "job_requirement": "AWS",
            "resume_chunk": "Unrelated resume detail.",
            "similarity_score": 0.2,
            "chunk_id": "chunk_1",
        },
    ]

    filtered = filter_top_matches(matches, min_similarity=0.35)

    assert len(filtered) == 1
    assert filtered[0]["job_requirement"] == "Python"


def test_filter_top_matches_sorts_by_similarity_descending():
    matches = [
        {
            "job_requirement": "SQL",
            "resume_chunk": "Used SQL.",
            "similarity_score": 0.45,
        },
        {
            "job_requirement": "Python",
            "resume_chunk": "Used Python.",
            "similarity_score": 0.82,
        },
    ]

    filtered = filter_top_matches(matches)

    assert [match["job_requirement"] for match in filtered] == ["Python", "SQL"]


def test_filter_top_matches_removes_duplicate_resume_chunks():
    matches = [
        {
            "job_requirement": "Python",
            "resume_chunk": "Built backend APIs.",
            "similarity_score": 0.8,
            "chunk_id": "chunk_0",
        },
        {
            "job_requirement": "FastAPI",
            "resume_chunk": "Built backend APIs.",
            "similarity_score": 0.7,
            "chunk_id": "chunk_0",
        },
    ]

    filtered = filter_top_matches(matches)

    assert len(filtered) == 1
    assert filtered[0]["job_requirement"] == "Python"


def test_calculate_match_score_returns_0_to_100():
    score = calculate_match_score(
        matched_skill_count=20,
        job_skill_count=3,
        semantic_matches=[{"similarity_score": 2.0}],
        resume_chunk_count=5,
    )

    assert 0 <= score <= 100


def test_calculate_match_score_increases_with_more_evidence():
    low_score = calculate_match_score(
        matched_skill_count=1,
        job_skill_count=5,
        semantic_matches=[{"similarity_score": 0.4}],
        resume_chunk_count=4,
    )
    high_score = calculate_match_score(
        matched_skill_count=4,
        job_skill_count=5,
        semantic_matches=[{"similarity_score": 0.8}, {"similarity_score": 0.7}],
        resume_chunk_count=4,
    )

    assert high_score > low_score


def test_calculate_match_score_handles_zero_job_skills():
    score = calculate_match_score(
        matched_skill_count=0,
        job_skill_count=0,
        semantic_matches=[{"similarity_score": 0.7}],
        resume_chunk_count=3,
    )

    assert 0 <= score <= 100
    assert score > 0


def test_build_summary_changes_for_high_medium_and_low_scores():
    high = build_summary(82, 5, 1, 4)
    medium = build_summary(61, 3, 2, 2)
    low = build_summary(32, 1, 4, 0)

    assert "strong match" in high
    assert "partial match" in medium
    assert "low match" in low
    assert "estimate" in high


def test_high_priority_missing_reduces_score():
    """A resume missing the job's specialized 'High'-priority skills should
    score lower than a resume that has the same number of generic matches
    but does not miss any high-priority requirement."""
    base = calculate_match_score(
        matched_skill_count=3,
        job_skill_count=10,
        semantic_matches=[{"similarity_score": 0.6}],
        resume_chunk_count=5,
        high_priority_missing_count=0,
        high_priority_job_count=0,
    )
    penalized = calculate_match_score(
        matched_skill_count=3,
        job_skill_count=10,
        semantic_matches=[{"similarity_score": 0.6}],
        resume_chunk_count=5,
        high_priority_missing_count=5,
        high_priority_job_count=5,
    )
    assert penalized < base
    # Penalty must remain bounded (cap is 20 points).
    assert base - penalized <= 21


def test_score_stays_in_0_to_100_with_penalty():
    score = calculate_match_score(
        matched_skill_count=0,
        job_skill_count=10,
        semantic_matches=[{"similarity_score": 0.0}],
        resume_chunk_count=2,
        high_priority_missing_count=10,
        high_priority_job_count=10,
    )
    assert 0 <= score <= 100


def test_specialized_role_with_many_missing_core_skills_scores_low_or_partial():
    """Resume mentions 1 of 10 job skills, all 6 specialized ones missing,
    semantic evidence is weak. Score should be low/partial — not high."""
    score = calculate_match_score(
        matched_skill_count=1,
        job_skill_count=10,
        semantic_matches=[{"similarity_score": 0.4}],
        resume_chunk_count=4,
        high_priority_missing_count=6,
        high_priority_job_count=6,
    )
    assert score <= 50


def test_strong_semantic_does_not_override_missing_core_requirements():
    """Even with strong semantic evidence, missing every high-priority skill
    should still pull the score below a 'strong match' (>= 75)."""
    score = calculate_match_score(
        matched_skill_count=2,
        job_skill_count=10,
        semantic_matches=[
            {"similarity_score": 0.95},
            {"similarity_score": 0.95},
            {"similarity_score": 0.9},
        ],
        resume_chunk_count=4,
        high_priority_missing_count=6,
        high_priority_job_count=6,
    )
    assert score < 75
