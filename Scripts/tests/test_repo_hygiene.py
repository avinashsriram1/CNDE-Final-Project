"""Repo hygiene checks (Part D, K2).

These guard the rules that would hurt us most if broken on a public repo:
required folder structure, no secrets, no raw data, no course-proprietary files.
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAX_FILE_BYTES = 5 * 1024 * 1024  # "no file over a few MB in git" (DEV-04)

REQUIRED_PATHS = [
    "README.md",
    "References.md",
    "AI_USAGE.md",
    "Docs",
    "Scripts",
    "Docker",
    ".github/workflows",
    "BI",
    "Video",
]

FORBIDDEN_NAMES = {
    ".env",
    "CNDE-FinalProject.pdf",
    "afdc_stations.json",
    "afdc_stations.csv",
    "afdc_registrations.csv",
    "eia_residential_prices.csv",
}
FORBIDDEN_DIR_PARTS = {"Module3_Exercises", "data"}


def tracked_files() -> list[Path]:
    """Files git would commit; falls back to a filesystem walk outside a git checkout."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [REPO_ROOT / line for line in out.splitlines() if line]
    except (subprocess.CalledProcessError, FileNotFoundError):
        skip = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
        return [
            p
            for p in REPO_ROOT.rglob("*")
            if p.is_file() and not skip.intersection(p.relative_to(REPO_ROOT).parts)
        ]


@pytest.mark.parametrize("rel_path", REQUIRED_PATHS)
def test_required_structure_exists(rel_path):
    assert (REPO_ROOT / rel_path).exists(), f"Spec Section 9 requires {rel_path}"


def test_no_large_files():
    too_big = [
        str(p.relative_to(REPO_ROOT))
        for p in tracked_files()
        if p.exists() and p.stat().st_size > MAX_FILE_BYTES
    ]
    assert not too_big, f"Files over 5 MB belong in GCS, not git: {too_big}"


def test_no_forbidden_files():
    bad = []
    for p in tracked_files():
        rel = p.relative_to(REPO_ROOT)
        if rel.name in FORBIDDEN_NAMES or FORBIDDEN_DIR_PARTS.intersection(rel.parts[:-1]):
            bad.append(str(rel))
    assert not bad, f"Secrets, raw data, or course material in repo: {bad}"


def test_gitignore_covers_secrets_and_data():
    rules = (REPO_ROOT / ".gitignore").read_text().splitlines()
    for required in [".env", "data/", "CNDE-FinalProject.pdf", "Module3_Exercises/"]:
        assert required in rules, f".gitignore must contain {required!r}"


def test_env_example_has_no_values_for_secrets():
    """Keys and passwords must be blank in the committed template (GOV-02)."""
    secret_markers = ("KEY", "TOKEN", "PASSWORD", "SECRET")
    for line in (REPO_ROOT / "Docker" / ".env.example").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if any(m in key.upper() for m in secret_markers):
            assert value.strip() == "", f"{key} must be empty in .env.example"
