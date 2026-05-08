"""Unit tests for app.job_parser module."""

import pytest

from app.job_parser import (
    SKILL_CATALOG,
    classify_skill_importance,
    clean_job_description,
    extract_skills_from_text,
)


# ---- clean_job_description ----

class TestCleanJobDescription:
    """Tests for clean_job_description."""

    def test_strips_whitespace(self):
        raw = "   We need a Python developer.  Experience with Docker and AWS required. Must know SQL and FastAPI.   "
        result = clean_job_description(raw)
        assert result == "We need a Python developer. Experience with Docker and AWS required. Must know SQL and FastAPI."
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_collapses_repeated_spaces(self):
        raw = "We  need   a    Python developer with FastAPI experience and Docker skills for our team."
        result = clean_job_description(raw)
        assert "  " not in result

    def test_collapses_repeated_blank_lines(self):
        raw = "We need a Python developer.\n\n\n\n\nMust know Docker, AWS, SQL, and FastAPI for this role."
        result = clean_job_description(raw)
        assert "\n\n\n" not in result

    def test_rejects_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            clean_job_description("Hi")

    def test_rejects_only_whitespace(self):
        with pytest.raises(ValueError, match="too short"):
            clean_job_description("          ")

    def test_accepts_exactly_50_chars(self):
        text = "a" * 50
        result = clean_job_description(text)
        assert len(result) == 50

    def test_rejects_49_chars(self):
        with pytest.raises(ValueError, match="too short"):
            clean_job_description("a" * 49)


# ---- extract_skills_from_text ----

class TestExtractSkillsFromText:
    """Tests for extract_skills_from_text."""

    def test_finds_single_skill(self):
        skills = extract_skills_from_text("We use Python for backend work every single day at our company.")
        assert "Python" in skills

    def test_finds_multiple_skills(self):
        text = "We need Python, FastAPI, and Docker experience for our cloud-based backend infrastructure project."
        skills = extract_skills_from_text(text)
        assert "Python" in skills
        assert "FastAPI" in skills
        assert "Docker" in skills

    def test_case_insensitive(self):
        skills = extract_skills_from_text("Experience with PYTHON, fastapi, and docker required for this backend role at our company.")
        assert "Python" in skills
        assert "FastAPI" in skills
        assert "Docker" in skills

    def test_no_duplicates(self):
        text = "Python Python python PYTHON experience with Python and more Python for our backend infrastructure."
        skills = extract_skills_from_text(text)
        assert skills.count("Python") == 1

    def test_returns_canonical_names(self):
        text = "Experience with nodejs, sklearn, and k8s in production-grade cloud infrastructure deployments."
        skills = extract_skills_from_text(text)
        assert "Node.js" in skills
        assert "scikit-learn" in skills
        assert "Kubernetes" in skills

    def test_no_false_positive_git_in_digital(self):
        """'digital' should NOT match 'git'."""
        skills = extract_skills_from_text("We are a digital marketing company building amazing customer experiences every day.")
        assert "Git" not in skills

    def test_empty_text(self):
        skills = extract_skills_from_text("")
        assert skills == []

    def test_no_skills_found(self):
        skills = extract_skills_from_text("We are looking for a great team player with strong communication and analytical abilities.")
        assert skills == []

    def test_order_is_deterministic(self):
        text = "Docker, Python, FastAPI, and SQL experience needed for our backend infrastructure development."
        first = extract_skills_from_text(text)
        second = extract_skills_from_text(text)
        assert first == second

    def test_multiword_skill_rest_api(self):
        skills = extract_skills_from_text("Must have experience building REST API services for enterprise-grade backend infrastructure.")
        assert "REST API" in skills

    def test_cicd_variants(self):
        for variant in ["CI/CD", "ci cd", "cicd"]:
            padded = f"Experience with {variant} pipelines is strongly required for this senior backend engineering role."
            skills = extract_skills_from_text(padded)
            assert "CI/CD" in skills, f"'{variant}' should match CI/CD"


# ---- Specialized skill detection (compilers, quantum, hardware, algorithms) ----


class TestSpecializedSkillDetection:
    """Tests for the expanded specialized-role skill catalog."""

    def test_detects_cpp_and_python(self):
        text = (
            "Strong proficiency in C++ and Python. Experience with software "
            "systems and performance-sensitive code is required."
        )
        skills = extract_skills_from_text(text)
        assert "C++" in skills
        assert "Python" in skills

    def test_detects_c_with_cpp_context(self):
        text = (
            "We need engineers fluent in C, C++, and Python with a strong "
            "computer science background and systems experience."
        )
        skills = extract_skills_from_text(text)
        assert "C" in skills
        assert "C++" in skills

    def test_detects_compiler_architecture(self):
        text = (
            "Background in compiler architecture or compiler internals is a "
            "must. You will work on intermediate representations and passes."
        )
        skills = extract_skills_from_text(text)
        assert "Compiler Architecture" in skills
        assert "Intermediate Representation" in skills

    def test_detects_quantum_computing(self):
        text = (
            "Join our quantum computing team to build the next generation of "
            "quantum computers and software stack."
        )
        skills = extract_skills_from_text(text)
        assert "Quantum Computing" in skills

    def test_detects_quantum_error_correction_qec(self):
        text = (
            "Experience in quantum error correction (QEC) and "
            "fault-tolerant computing is preferred."
        )
        skills = extract_skills_from_text(text)
        assert "Quantum Error Correction" in skills
        assert "Fault-Tolerant Computing" in skills

    def test_detects_hpc(self):
        text = (
            "Familiarity with high-performance computing or HPC workloads "
            "and scientific computing is required."
        )
        skills = extract_skills_from_text(text)
        assert "High-Performance Computing" in skills
        assert "Scientific Computing" in skills

    def test_detects_gpu_programming_and_cuda(self):
        text = (
            "GPU programming experience, ideally with CUDA, and knowledge "
            "of hardware acceleration are required."
        )
        skills = extract_skills_from_text(text)
        assert "GPU Programming" in skills
        assert "CUDA" in skills
        assert "Hardware Acceleration" in skills

    def test_detects_fpga_and_dsp(self):
        text = (
            "Hands-on experience with FPGA and DSP development for "
            "real-time computing is highly desired."
        )
        skills = extract_skills_from_text(text)
        assert "FPGA" in skills
        assert "DSP" in skills
        assert "Real-Time Computing" in skills

    def test_detects_graph_algorithms_and_matching(self):
        text = (
            "Deep knowledge of graph algorithms, including weighted perfect "
            "matching, and dynamic programming is needed."
        )
        skills = extract_skills_from_text(text)
        assert "Graph Algorithms" in skills
        assert "Weighted Perfect Matching" in skills
        assert "Dynamic Programming" in skills

    def test_detects_kernel_and_driver_development(self):
        text = (
            "Linux kernel development and device driver programming "
            "experience preferred for this systems role."
        )
        skills = extract_skills_from_text(text)
        assert "Kernel Development" in skills
        assert "Driver Development" in skills

    def test_detects_concurrency_and_parallel_programming(self):
        text = (
            "Strong experience in concurrency and parallel programming "
            "across distributed systems is required."
        )
        skills = extract_skills_from_text(text)
        assert "Concurrency" in skills
        assert "Parallel Programming" in skills
        assert "Distributed Systems" in skills

    def test_detects_logic_synthesis_and_quantum_compiler(self):
        text = (
            "Knowledge of logic synthesis, quantum compilation, and quantum "
            "compiler infrastructure is highly valued."
        )
        skills = extract_skills_from_text(text)
        assert "Logic Synthesis" in skills
        assert "Quantum Compiler" in skills


class TestFalsePositives:
    """Tests that ambiguous tokens do not match inside ordinary words."""

    def test_no_false_positive_letter_c(self):
        """'C' must not match inside random words like 'process' or 'section'."""
        text = (
            "We process every section of the document and orchestrate each "
            "service with careful attention to compliance and acceptance."
        )
        skills = extract_skills_from_text(text)
        assert "C" not in skills
        assert "C++" not in skills

    def test_no_false_positive_ir_inside_words(self):
        """'IR' must not match inside words like 'first', 'their', 'fire'."""
        text = (
            "First-class candidates have built their own service platforms "
            "and fire-tested them under heavy load. We aim to hire fast."
        )
        skills = extract_skills_from_text(text)
        assert "Intermediate Representation" not in skills

    def test_ir_only_matches_with_strong_compiler_context(self):
        text = (
            "You will work on LLVM IR passes, MLIR lowering, and design "
            "the next intermediate representation for our compiler."
        )
        skills = extract_skills_from_text(text)
        assert "Intermediate Representation" in skills


class TestOrderAndDeduplication:
    """Tests that order is deterministic and there are no duplicates."""

    def test_predictable_specialized_order(self):
        text = (
            "Looking for engineers with FPGA, Python, GPU programming, "
            "C++, quantum computing, and graph algorithms experience."
        )
        skills_first = extract_skills_from_text(text)
        skills_second = extract_skills_from_text(text)
        assert skills_first == skills_second

        # Order must follow SKILL_CATALOG order, not text order.
        catalog_order = list(SKILL_CATALOG.keys())
        positions = [catalog_order.index(s) for s in skills_first]
        assert positions == sorted(positions)

    def test_specialized_skills_no_duplicates(self):
        text = (
            "C++ C++ c++ CPP-style C++ work; quantum computing and quantum "
            "computing again, plus QEC and quantum error correction."
        )
        skills = extract_skills_from_text(text)
        assert skills.count("C++") == 1
        assert skills.count("Quantum Computing") == 1
        assert skills.count("Quantum Error Correction") == 1


class TestNlpDoesNotDominate:
    """When the JD has many specialized signals, NLP must not be the headline."""

    def test_quantum_role_with_brief_nlp_mention(self):
        text = (
            "Minimum qualifications: C++, Python, compiler architecture, "
            "quantum computing, quantum error correction, high-performance "
            "computing, GPU programming, FPGA, graph algorithms, and "
            "concurrency. Some natural language processing exposure is a "
            "small bonus."
        )
        skills = extract_skills_from_text(text)
        # All specialized skills should be detected.
        for skill in [
            "Compiler Architecture",
            "Quantum Computing",
            "Quantum Error Correction",
            "High-Performance Computing",
            "GPU Programming",
            "FPGA",
            "Graph Algorithms",
            "Concurrency",
        ]:
            assert skill in skills, f"expected {skill} to be detected"
        # NLP can still appear — but it should not be the only or dominant
        # signal: many specialized skills outrank it.
        specialized = {
            s
            for s in skills
            if s
            in {
                "Compiler Architecture",
                "Quantum Computing",
                "Quantum Error Correction",
                "High-Performance Computing",
                "GPU Programming",
                "FPGA",
                "Graph Algorithms",
                "Concurrency",
            }
        }
        assert len(specialized) >= 5


# ---- classify_skill_importance ----


class TestClassifySkillImportance:
    """Tests for classify_skill_importance."""

    def test_high_when_under_minimum_qualifications(self):
        text = (
            "About the team: build great quantum software.\n\n"
            "Minimum qualifications:\n"
            "- BS in Computer Science\n"
            "- Strong experience in compiler architecture\n"
        )
        assert classify_skill_importance("Compiler Architecture", text) == "High"

    def test_medium_when_under_preferred_qualifications(self):
        text = (
            "Minimum qualifications: BS in CS.\n"
            "Preferred qualifications:\n"
            "- Familiarity with REST API design\n"
        )
        # REST API is not in HIGH_PRIORITY_SKILLS and not LOW broad term.
        assert classify_skill_importance("REST API", text) == "Medium"

    def test_high_for_specialized_term_even_in_preferred(self):
        text = (
            "Preferred qualifications: experience with FPGA development "
            "is a strong plus."
        )
        assert classify_skill_importance("FPGA", text) == "High"

    def test_low_for_broad_term_in_preferred_section(self):
        text = (
            "Minimum qualifications: BS degree.\n"
            "Preferred qualifications: familiarity with Linux and Git."
        )
        assert classify_skill_importance("Linux", text) == "Low"

    def test_specialized_default_high_with_no_section_signal(self):
        text = (
            "Our group builds high-performance computing systems for "
            "scientific simulation workloads."
        )
        assert (
            classify_skill_importance("High-Performance Computing", text) == "High"
        )

    def test_unknown_skill_defaults_medium(self):
        text = "We use REST API services across the platform."
        assert classify_skill_importance("REST API", text) == "Medium"

    def test_empty_text_returns_medium(self):
        assert classify_skill_importance("Python", "") == "Medium"
