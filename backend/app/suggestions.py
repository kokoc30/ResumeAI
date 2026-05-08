"""Rule-based resume suggestion helpers."""


# Skill groups for role-specific suggestion targeting (not used in scoring).
_QUANTUM_COMPILER_SYSTEMS_SET: frozenset[str] = frozenset(
    {
        "Quantum Computing",
        "Quantum Error Correction",
        "Quantum Compiler",
        "Fault-Tolerant Computing",
        "Compiler Architecture",
        "Intermediate Representation",
        "Logic Synthesis",
        "Kernel Development",
        "Driver Development",
        "High-Performance Computing",
        "Concurrency",
        "Parallel Programming",
        "Systems Programming",
        "Low-Level Programming",
        "Distributed Systems",
    }
)

_HARDWARE_SET: frozenset[str] = frozenset(
    {
        "FPGA",
        "DSP",
        "GPU Programming",
        "CUDA",
        "Hardware Acceleration",
    }
)

_ALGORITHM_SET: frozenset[str] = frozenset(
    {
        "Graph Algorithms",
        "Weighted Perfect Matching",
        "Dynamic Programming",
    }
)


def _average_similarity(semantic_matches: list[dict]) -> float:
    scores = [
        float(match.get("similarity_score", 0.0))
        for match in semantic_matches
        if match.get("similarity_score") is not None
    ]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def build_resume_suggestions(
    missing_skills: list[str],
    semantic_matches: list[dict],
    match_score: int,
) -> list[str]:
    """Return practical, honest resume suggestions without using an LLM.

    Suggestions are selected by which categories of missing skills appear
    (compiler/quantum/systems, hardware, algorithms) so advice stays
    targeted instead of generic. The output is capped at 5 items to keep
    the UI manageable.
    """
    suggestions: list[str] = []
    missing_set = set(missing_skills)

    if missing_skills:
        shown_skills = ", ".join(missing_skills[:3])
        pronoun = "it" if len(missing_skills[:3]) == 1 else "them"
        suggestions.append(
            f"Add {shown_skills} only if you have real experience with {pronoun}."
        )
    else:
        suggestions.append(
            "Keep the skills section aligned with the role and back each listed "
            "skill with real project or work evidence."
        )

    # Targeted advice for compiler / quantum / systems roles.
    if missing_set & _QUANTUM_COMPILER_SYSTEMS_SET:
        suggestions.append(
            "For compiler, quantum, or systems roles, only claim experience you "
            "actually have. If you want to target this role, build a small "
            "portfolio project involving compiler passes, intermediate "
            "representations, graph algorithms, or quantum simulation "
            "(for example with Qiskit or Cirq) and describe what it does."
        )

    if missing_set & _HARDWARE_SET:
        suggestions.append(
            "If you have CUDA, GPU, FPGA, or DSP project experience, describe "
            "what you optimized, the workload size, and the speedup achieved. "
            "Do not list these unless you can support them with real work."
        )

    if missing_set & _ALGORITHM_SET:
        suggestions.append(
            "If you have algorithms coursework, competitive programming, or "
            "research, name specific algorithms (graph, matching, dynamic "
            "programming) and the problems they solved."
        )

    average_similarity = _average_similarity(semantic_matches)
    if not semantic_matches or average_similarity < 0.55:
        suggestions.append(
            "Add measurable results to the most relevant bullets so the resume "
            "evidence is easier to match to the job description."
        )
    else:
        suggestions.append(
            "Strengthen the best-matching bullets with concrete outcomes, tools "
            "used, and scope of responsibility."
        )

    if match_score < 50:
        suggestions.append(
            "Make projects and experience bullets more specific to this role by "
            "naming the languages, systems, and delivery results you actually used."
        )
    elif match_score < 75:
        suggestions.append(
            "Tighten the strongest experience bullets so they connect role "
            "requirements to specific work you completed."
        )
    else:
        suggestions.append(
            "Keep the strongest aligned evidence near the top of the resume so "
            "recruiters see it quickly."
        )

    if len(missing_skills) > 3:
        suggestions.append(
            "Prioritize the missing skills that matter most to the job, and only "
            "include them when you can support them with honest examples."
        )

    if len(suggestions) < 4:
        suggestions.append(
            "Use clear role keywords naturally in project and experience bullets "
            "when they accurately describe your work."
        )

    return suggestions[:5]
