"""Job description parsing utilities.

Cleans raw job description text and extracts skills using a richer local
skill catalog (no external ML/LLM required).

The catalog covers basic programming/web/ML skills plus specialized topics
like compilers, quantum computing, HPC/concurrency, hardware acceleration,
and graph algorithms. Detection uses word-boundary regex matching plus a
few carefully designed regex patterns for ambiguous tokens (e.g. "C", "IR")
to avoid false positives inside ordinary words.
"""

import re

from app.utils import clean_text, validate_minimum_text_length


# Skill catalog: canonical name -> aliases (word-boundary matched, case-insensitive).
# Ambiguous tokens like "C" or "IR" use raw regex in SKILL_REGEX_PATTERNS below.
SKILL_CATALOG: dict[str, list[str]] = {
    # --- Programming languages ---
    "Python": ["python"],
    "C++": [],
    "C": [],
    "Java": ["java"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "Assembly": ["assembly", "x86 assembly", "arm assembly"],
    "Rust": ["rust"],
    "Bash": ["bash"],

    # --- Web / API ---
    "HTML": ["html"],
    "CSS": ["css"],
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Django": ["django"],
    "React": ["react"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "Express": ["express"],
    "REST API": ["rest api", "restful api", "rest apis"],
    "API": ["api"],

    # --- Databases ---
    "SQL": ["sql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "MongoDB": ["mongodb", "mongo"],
    "Supabase": ["supabase"],

    # --- Cloud / DevOps ---
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "GCP": ["gcp", "google cloud"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Git": ["git"],
    "GitHub": ["github"],
    "CI/CD": ["ci/cd", "ci cd", "cicd"],
    "Linux": ["linux"],

    # --- Software / Systems ---
    "Software Systems": ["software systems"],
    "Systems Programming": ["systems programming", "system programming"],
    "Low-Level Programming": [
        "low-level programming",
        "low level programming",
        "low-level software",
    ],
    "Operating Systems": ["operating systems"],
    "Computer Architecture": ["computer architecture"],
    "Embedded Systems": ["embedded systems", "embedded programming"],
    "Arduino": ["arduino"],
    "IoT": ["iot", "internet of things"],

    # --- Compilers ---
    "Compiler Architecture": [
        "compiler architecture",
        "compiler design",
        "compiler internals",
        "compiler development",
    ],
    "Intermediate Representation": [],
    "Quantum Compiler": [
        "quantum compiler",
        "quantum compilers",
        "quantum compilation",
    ],
    "Logic Synthesis": ["logic synthesis"],

    # --- Quantum ---
    "Quantum Computing": [
        "quantum computing",
        "quantum computer",
        "quantum computers",
    ],
    "Quantum Error Correction": [
        "quantum error correction",
        "qec",
    ],
    "Fault-Tolerant Computing": [
        "fault-tolerant computing",
        "fault tolerant computing",
        "fault tolerance",
    ],
    "Qiskit": ["qiskit"],
    "Cirq": ["cirq"],

    # --- Performance / concurrency ---
    "High-Performance Computing": [
        "high-performance computing",
        "high performance computing",
        "hpc",
    ],
    "Real-Time Computing": [
        "real-time computing",
        "real time computing",
    ],
    "Kernel Development": [
        "kernel development",
        "kernel programming",
        "linux kernel",
    ],
    "Driver Development": [
        "driver development",
        "device driver",
        "device drivers",
    ],
    "Concurrency": ["concurrency", "concurrent programming"],
    "Parallel Programming": [
        "parallel programming",
        "parallel computing",
    ],
    "Scientific Computing": ["scientific computing"],
    "Distributed Systems": ["distributed systems"],

    # --- Hardware acceleration ---
    "Hardware Acceleration": [
        "hardware acceleration",
        "hardware accelerator",
        "hardware accelerators",
    ],
    "GPU Programming": [
        "gpu programming",
        "gpu computing",
        "programming gpus",
        "gpu development",
    ],
    "CUDA": ["cuda"],
    "FPGA": ["fpga"],
    "DSP": ["dsp", "digital signal processing"],

    # --- Algorithms ---
    "Graph Algorithms": ["graph algorithms", "graph algorithm"],
    "Weighted Perfect Matching": [
        "weighted perfect matching",
        "perfect matching",
    ],
    "Algorithms": ["algorithms"],
    "Data Structures": ["data structures", "data structure"],
    "Dynamic Programming": ["dynamic programming"],

    # --- AI / ML ---
    "Machine Learning": ["machine learning"],
    "Deep Learning": ["deep learning"],
    "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision"],
    "Reinforcement Learning": ["reinforcement learning"],
    "Convolutional Neural Networks": [
        "convolutional neural networks",
        "convolutional neural network",
        "cnns",
    ],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Keras": ["keras"],
    "OpenCV": ["opencv"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
}

# Raw regex for ambiguous tokens that need context-aware matching.
SKILL_REGEX_PATTERNS: dict[str, list[str]] = {
    # C++ — escape `+` and forbid trailing `+` to avoid odd "c+++" matches.
    "C++": [r"\bc\+\+(?!\+)"],

    # C — only match in contexts that strongly imply the C language so
    # ordinary words like "process" or "section c" do not produce a hit.
    "C": [
        r"\bc/c\+\+",
        r"\bc\+\+/c\b(?!\+)",
        r"\bc\s*,\s*c\+\+",
        r"c\+\+\s*,\s*c\b(?!\+)",
        r"\bc\s+and\s+c\+\+",
        r"c\+\+\s+and\s+c\b(?!\+)",
        r"\bc\s+programming\b",
        r"\bc\s+language\b",
        r"\b(?:in|with|using|knowledge\s+of|experience\s+(?:in|with))\s+c\b(?!\+)",
        r"\bc\s*,\s*(?:python|java|javascript|assembly|rust|go)\b",
        r"\b(?:python|java|javascript|assembly|rust|go)\s*,\s*c\b(?!\+)",
    ],

    # Intermediate Representation — multi-word phrase or "IR" only when
    # the surrounding text strongly implies a compiler IR.
    "Intermediate Representation": [
        r"\bintermediate\s+representations?\b",
        r"\bllvm\s+ir\b",
        r"\bmlir\b",
        r"\bcompiler\s+ir\b",
        r"\bir\s+(?:pass|passes|generation|optimi[sz]ation|lowering)\b",
    ],
}


def _build_compiled_patterns() -> dict[str, list[re.Pattern[str]]]:
    """Compile both literal aliases and raw regex into one dict (ordered)."""
    compiled: dict[str, list[re.Pattern[str]]] = {}
    for skill, aliases in SKILL_CATALOG.items():
        patterns: list[re.Pattern[str]] = []
        for alias in aliases:
            patterns.append(
                re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
            )
        for raw in SKILL_REGEX_PATTERNS.get(skill, []):
            patterns.append(re.compile(raw, re.IGNORECASE))
        if patterns:
            compiled[skill] = patterns
    return compiled


_COMPILED_PATTERNS: dict[str, list[re.Pattern[str]]] = _build_compiled_patterns()


# Skills that default to "High" importance for specialized roles.
HIGH_PRIORITY_SKILLS: set[str] = {
    "Python",
    "C++",
    "C",
    "Compiler Architecture",
    "Intermediate Representation",
    "Quantum Computing",
    "Quantum Error Correction",
    "Quantum Compiler",
    "Fault-Tolerant Computing",
    "Logic Synthesis",
    "High-Performance Computing",
    "Concurrency",
    "Parallel Programming",
    "Kernel Development",
    "Driver Development",
    "Hardware Acceleration",
    "GPU Programming",
    "CUDA",
    "FPGA",
    "DSP",
    "Graph Algorithms",
    "Weighted Perfect Matching",
    "Systems Programming",
    "Low-Level Programming",
    "Distributed Systems",
}

# Broad terms that default to "Low" importance.
LOW_PRIORITY_BROAD_TERMS: set[str] = {
    "API",
    "HTML",
    "CSS",
    "Algorithms",
    "Data Structures",
    "Operating Systems",
    "Linux",
    "Git",
    "GitHub",
}


_HIGH_SIGNAL_PHRASES: tuple[str, ...] = (
    "minimum qualifications",
    "required qualifications",
    "required skills",
    "must have",
    "requirements:",
    "what you'll need",
    "what you need",
    "you have:",
)
_MEDIUM_SIGNAL_PHRASES: tuple[str, ...] = (
    "preferred qualifications",
    "preferred skills",
    "nice to have",
    "responsibilities",
    "bonus",
)


MIN_JOB_DESC_LENGTH = 50


def clean_job_description(text: str) -> str:
    """Normalize whitespace and validate a job description. Raises ValueError if too short."""
    cleaned = clean_text(text)
    validate_minimum_text_length(cleaned, "Job description", MIN_JOB_DESC_LENGTH)
    return cleaned


def extract_skills_from_text(text: str) -> list[str]:
    """Find known skills in text using the catalog. Returns in catalog order, no duplicates."""
    found: list[str] = []
    for skill, patterns in _COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                found.append(skill)
                break
    return found


def _find_first_skill_position(skill: str, text: str) -> int:
    """Return the lowest start index where any pattern for *skill* matches.

    Returns -1 when no pattern matches.
    """
    earliest = -1
    for pattern in _COMPILED_PATTERNS.get(skill, []):
        match = pattern.search(text)
        if match is None:
            continue
        if earliest < 0 or match.start() < earliest:
            earliest = match.start()
    return earliest


def classify_skill_importance(skill: str, job_text: str) -> str:
    """Classify a skill's importance to the given job description.

    Returns one of "High", "Medium", "Low".

    Rules (kept simple and explainable):
    - If the skill appears under a "minimum qualifications" / "required" /
      "must have" section, importance is High.
    - If it appears under a "preferred" / "nice to have" / "responsibilities"
      section, importance is Medium (or Low for broad/secondary terms).
    - Specialized terms in ``HIGH_PRIORITY_SKILLS`` default to High when the
      section context is unclear, since they carry strong role signal.
    - Broad/secondary terms in ``LOW_PRIORITY_BROAD_TERMS`` default to Low.
    - Everything else defaults to Medium.
    """
    if not job_text:
        return "Medium"

    position = _find_first_skill_position(skill, job_text)
    lower_before = job_text[:position].lower() if position >= 0 else ""

    last_high = max(
        (lower_before.rfind(p) for p in _HIGH_SIGNAL_PHRASES), default=-1
    )
    last_medium = max(
        (lower_before.rfind(p) for p in _MEDIUM_SIGNAL_PHRASES), default=-1
    )

    if position >= 0:
        if last_high > last_medium and last_high >= 0:
            return "High"
        if last_medium > last_high and last_medium >= 0:
            if skill in HIGH_PRIORITY_SKILLS:
                return "High"
            if skill in LOW_PRIORITY_BROAD_TERMS:
                return "Low"
            return "Medium"

    if skill in HIGH_PRIORITY_SKILLS:
        return "High"
    if skill in LOW_PRIORITY_BROAD_TERMS:
        return "Low"
    return "Medium"
