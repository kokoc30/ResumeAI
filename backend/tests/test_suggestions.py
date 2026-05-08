from app.suggestions import build_resume_suggestions


def test_suggestions_mention_missing_skills_honestly():
    suggestions = build_resume_suggestions(
        missing_skills=["AWS"],
        semantic_matches=[{"similarity_score": 0.7}],
        match_score=68,
    )

    assert any("AWS" in suggestion for suggestion in suggestions)
    assert any("only if you have real experience" in suggestion for suggestion in suggestions)


def test_suggestions_do_not_tell_user_to_fake_or_lie():
    suggestions = build_resume_suggestions(
        missing_skills=["Docker", "AWS"],
        semantic_matches=[],
        match_score=35,
    )
    combined = " ".join(suggestions).lower()

    assert "fake" not in combined
    assert "lie" not in combined


def test_suggestions_return_useful_number_of_items():
    suggestions = build_resume_suggestions(
        missing_skills=["SQL"],
        semantic_matches=[{"similarity_score": 0.6}],
        match_score=72,
    )

    assert 3 <= len(suggestions) <= 5


def test_low_score_gives_stronger_improvement_suggestions():
    suggestions = build_resume_suggestions(
        missing_skills=["FastAPI"],
        semantic_matches=[],
        match_score=28,
    )

    assert any("more specific" in suggestion for suggestion in suggestions)
    assert any("measurable results" in suggestion for suggestion in suggestions)


# ---- Targeted advice for specialized role categories ----


def test_quantum_compiler_missing_produces_targeted_advice():
    suggestions = build_resume_suggestions(
        missing_skills=[
            "Quantum Computing",
            "Compiler Architecture",
            "Quantum Error Correction",
            "High-Performance Computing",
        ],
        semantic_matches=[],
        match_score=42,
    )
    combined = " ".join(suggestions).lower()
    assert "compiler" in combined or "quantum" in combined
    assert "real experience" in combined


def test_hardware_acceleration_missing_produces_targeted_advice():
    suggestions = build_resume_suggestions(
        missing_skills=["FPGA", "CUDA", "GPU Programming"],
        semantic_matches=[{"similarity_score": 0.4}],
        match_score=38,
    )
    combined = " ".join(suggestions).lower()
    assert (
        "cuda" in combined
        or "gpu" in combined
        or "fpga" in combined
        or "dsp" in combined
    )


def test_suggestions_never_tell_user_to_fake_skills():
    suggestions = build_resume_suggestions(
        missing_skills=[
            "Quantum Computing",
            "Compiler Architecture",
            "FPGA",
            "CUDA",
            "Graph Algorithms",
        ],
        semantic_matches=[],
        match_score=30,
    )
    combined = " ".join(suggestions).lower()
    assert "fake" not in combined
    assert "lie" not in combined
    assert "make up" not in combined
    assert "pretend" not in combined


def test_specialized_missing_keeps_suggestions_count_reasonable():
    suggestions = build_resume_suggestions(
        missing_skills=[
            "Quantum Computing",
            "Compiler Architecture",
            "FPGA",
            "Graph Algorithms",
            "Concurrency",
            "Kernel Development",
        ],
        semantic_matches=[],
        match_score=35,
    )
    assert 3 <= len(suggestions) <= 5


def test_missing_skills_are_presented_with_real_experience_warning():
    suggestions = build_resume_suggestions(
        missing_skills=["Quantum Computing", "FPGA", "CUDA"],
        semantic_matches=[],
        match_score=40,
    )
    assert any("real experience" in suggestion for suggestion in suggestions)
