"""
test_repository_analyzer.py
===========================
Tests for Person A's repository_analyzer module:
- Online GitHub repository analysis (analyze_repository)
- Local directory scanning (scan_repository)
- Organization & Structure Analysis integration
"""

from pathlib import Path
from unittest.mock import patch
import pytest
from backend.repository_analyzer import analyze_repository, scan_repository, parse_github_url

def test_language_api_failure_is_reported():
    with patch(
        "repository_analyzer._github_api_request",
        side_effect=[
            (
                {
                    "name": "demo",
                    "description": "Demo repository",
                    "default_branch": "main",
                    "license": None,
                },
                200,
                None,
            ),
            (None, 403, "GitHub API rate limit exceeded."),
                        (
                {
                    "tree": [
                        {"type": "blob", "path": "README.md"}
                    ]
                },
                200,
                None,
            ),
        ],
    ):
        result = analyze_repository("https://github.com/octocat/demo")

    assert result["languages"] == {}

def test_online_analyzer():
    print("Testing online analyze_repository...")
    url = "https://github.com/octocat/Hello-World"
    result = analyze_repository(url)
    print("Repo Name:", result["repo_name"])
    print("Default Branch:", result["default_branch"])
    print("Files found:", result["files"])
    print("README exists:", result["readme_exists"])
    print("Organization Analysis:", "Present" if result.get("organization") else "Missing")
    if result["error"]:
        if "Network error" in result["error"] or "timed out" in result["error"].lower():
            pytest.skip(f"GitHub integration test requires network access: {result['error']}")
        pytest.fail(result["error"])
    assert result["readme_exists"] is True
    assert result.get("organization") is not None
    assert "file_classification" in result["organization"]
    print("[PASS] Online repository analyzer test passed!\n")

def test_parse_github_url_preserves_repo_name_ending_in_git_chars():
    owner, repo, error = parse_github_url(
        "https://github.com/octocat/legit"
    )

    assert owner == "octocat"
    assert repo == "legit"
    assert error is None

def test_local_scanner():
    print("Testing local scan_repository...")
    project_root = Path(__file__).resolve().parents[1]
    result = scan_repository(project_root)
    print("Repository:", result["repository_path"])
    print("Total files:", result["total_files"])
    print("Architecture Detected:", result["organization"]["project_conventions"]["architecture_type"])
    assert result["total_files"] > 0
    assert result.get("organization") is not None
    print("[PASS] Local scanner test passed!\n")

if __name__ == "__main__":
    test_online_analyzer()
    test_local_scanner()
