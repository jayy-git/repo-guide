"""
repository_analyzer.py
======================
Role: Person A (Repository Analyzer)
Project: RepoGuide

Mission:
Takes a public GitHub repository URL, retrieves metadata and file structure
using the GitHub REST API, and returns a normalized dictionary matching the
shared team contract. Handles all network, validation, and API errors gracefully.

Also includes comprehensive repository structure and organization analysis:
- Directory analysis
- File classification
- Project convention detection
- Organisation issue detection
- Folder structure recommendations
- Dependency and configuration review
- Change planning
- Organisation report
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.organization_analyzer import analyze_organization

# =====================================================================
# PART 1: Online GitHub Repository Analyzer (Person A Core Assignment)
# =====================================================================

def _build_default_repo_data(repo_url: Optional[str] = "", error: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a standardized dictionary following the team data contract.
    Ensures that downstream teammates (B, C, D) always receive the exact same keys
    and types, even when an error occurs.
    """
    return {
        "repo_url": str(repo_url or ""),
        "repo_name": "",
        "description": "",
        "default_branch": "",
        "files": [],
        "languages": {},
        "readme_exists": False,
        "license_exists": False,
        "contributing_exists": False,
        "requirements_files": [],
        "organization": None,
        "error": error
    }


def parse_github_url(repo_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parses and validates a GitHub repository URL.
    
    Accepts formats such as:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - https://github.com/owner/repo/
      - http://github.com/owner/repo
      - github.com/owner/repo
    """
    if not repo_url or not isinstance(repo_url, str):
        return None, None, "Repository URL cannot be empty."

    cleaned_url = repo_url.strip()
    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = "https://" + cleaned_url

    parsed = urllib.parse.urlparse(cleaned_url)
    
    # Verify domain is github.com
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("github.com", "www.github.com"):
        return None, None, f"Invalid domain '{hostname}'. RepoGuide only supports public GitHub repositories (github.com)."

    # Extract path parts
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]

    if len(parts) < 2:
        return None, None, "Invalid GitHub repository URL. Expected format: https://github.com/owner/repo"

    owner = parts[0]
    repo = parts[1]

    # Regex validation for GitHub usernames and repo names
    if not re.match(r"^[A-Za-z0-9_.-]+$", owner) or not re.match(r"^[A-Za-z0-9_.-]+$", repo):
        return None, None, f"URL contains invalid characters for owner ('{owner}') or repo ('{repo}')."

    return owner, repo, None


def _github_api_request(endpoint: str) -> Tuple[Optional[Any], Optional[int], Optional[str]]:
    """
    Makes a GET request to GitHub's REST API.
    - Uses unauthenticated access by default (60 requests/hour limit).
    - If GITHUB_TOKEN environment variable is set, it uses it for authentication (5,000 req/hr).
    """
    api_url = f"https://api.github.com{endpoint}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "RepoGuide-RepositoryAnalyzer/1.0",
    }

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"

    req = urllib.request.Request(api_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            data = json.loads(body)
            return data, status_code, None

    except urllib.error.HTTPError as e:
        status_code = e.code
        e.close()
        if status_code == 404:
            return None, 404, "Repository not found. Please verify the URL or check if the repository is private."
        elif status_code == 403:
            return None, 403, "GitHub API rate limit exceeded. Public unauthenticated access is limited to 60 requests/hour. Please try again later or configure GITHUB_TOKEN."
        elif status_code == 409:
            return None, 409, "Repository is empty and contains no commits."
        else:
            return None, status_code, f"GitHub API error (HTTP {status_code}): {e.reason}"

    except urllib.error.URLError as e:
        return None, None, f"Network error connecting to GitHub: {e.reason}. Please check your internet connection."

    except json.JSONDecodeError:
        return None, None, "Received malformed JSON response from GitHub API."

    except TimeoutError:
        return None, None, "Request to GitHub API timed out after 12 seconds."

    except Exception as e:
        return None, None, f"Unexpected error during API request: {str(e)}"


def _detect_project_documents(files: List[str], repo_meta: Dict[str, Any]) -> Tuple[bool, bool, bool, List[str]]:
    """
    Analyzes the list of file paths to detect standard project documents:
      - README
      - LICENSE
      - CONTRIBUTING
      - Requirements/dependency files
    """
    files_lower = {f: f.lower() for f in files}

    # 1. README detection
    readme_exists = False
    for orig_f, low_f in files_lower.items():
        base = os.path.basename(low_f)
        dir_name = os.path.dirname(low_f)
        if base in ("readme", "readme.md", "readme.rst", "readme.txt", "readme.markdown") or base.startswith("readme."):
            if dir_name in ("", ".github"):
                readme_exists = True
                break

    # 2. LICENSE detection
    license_exists = bool(repo_meta.get("license"))
    if not license_exists:
        for orig_f, low_f in files_lower.items():
            base = os.path.basename(low_f)
            if base in ("license", "license.md", "license.txt", "licence", "licence.md", "licence.txt") or base.startswith("license."):
                license_exists = True
                break

    # 3. CONTRIBUTING detection
    contributing_exists = False
    for orig_f, low_f in files_lower.items():
        base = os.path.basename(low_f)
        dir_name = os.path.dirname(low_f)
        if base in ("contributing", "contributing.md", "contributing.rst", "contributing.txt") or base.startswith("contributing."):
            if dir_name in ("", ".github", "docs"):
                contributing_exists = True
                break

    # 4. Requirements / Dependency files detection
    requirements_files = []
    known_dep_files = {
        "pyproject.toml", "setup.py", "setup.cfg", "pipfile", "pipfile.lock",
        "environment.yml", "environment.yaml", "package.json", "cargo.toml",
        "go.mod", "gemfile", "pom.xml", "build.gradle"
    }

    for orig_f, low_f in files_lower.items():
        base = os.path.basename(low_f)
        if "requirements" in base and base.endswith((".txt", ".in")):
            requirements_files.append(orig_f)
        elif base in known_dep_files:
            requirements_files.append(orig_f)

    requirements_files = sorted(list(set(requirements_files)))

    return readme_exists, license_exists, contributing_exists, requirements_files


def analyze_repository(repo_url: str) -> Dict[str, Any]:
    """
    Main entry point for Person A's module as per the revised team guide.
    
    Accepts a public GitHub repository URL, fetches repository facts, performs
    directory and organization analysis, and returns a normalized dictionary.
    """
    # Step 1: Validate and parse URL
    owner, repo, parse_error = parse_github_url(repo_url)
    if parse_error:
        return _build_default_repo_data(repo_url=repo_url, error=parse_error)

    normalized_url = f"https://github.com/{owner}/{repo}"

    # Step 2: Fetch Repository Metadata
    repo_meta, status, meta_error = _github_api_request(f"/repos/{owner}/{repo}")
    if meta_error:
        return _build_default_repo_data(repo_url=normalized_url, error=meta_error)

    repo_name = repo_meta.get("name", repo)
    description = repo_meta.get("description") or ""
    default_branch = repo_meta.get("default_branch") or "main"

    # Step 3: Fetch Programming Languages
    lang_data, _, _ = _github_api_request(f"/repos/{owner}/{repo}/languages")
    languages = lang_data if isinstance(lang_data, dict) else {}

    # Step 4: Fetch Recursive File Tree
    files: List[str] = []
    tree_data, tree_status, _ = _github_api_request(
        f"/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
    )

    if tree_data and isinstance(tree_data, dict) and "tree" in tree_data:
        for item in tree_data.get("tree", []):
            if item.get("type") == "blob" and "path" in item:
                files.append(item["path"])

    # Step 5: Detect project documents & requirements
    readme_exists, license_exists, contributing_exists, req_files = _detect_project_documents(files, repo_meta)

    # Step 6: Perform complete 8-part Organization & Structure Analysis
    organization_analysis = analyze_organization(files, repo_name=repo_name)

    # Step 7: Return normalized data dictionary matching team contract
    return {
        "repo_url": normalized_url,
        "repo_name": repo_name,
        "description": description,
        "default_branch": default_branch,
        "files": files,
        "languages": languages,
        "readme_exists": readme_exists,
        "license_exists": license_exists,
        "contributing_exists": contributing_exists,
        "requirements_files": req_files,
        "organization": organization_analysis,
        "error": None
    }


# =====================================================================
# PART 2: Local Directory Scanner (Backward Compatibility)
# =====================================================================

IGNORED_DIRECTORIES = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

IGNORED_FILES = {
    ".env", ".env.local", ".env.development", ".env.production", "ONBOARDING.md",
}

IGNORED_SUFFIXES = {
    ".pyc", ".pyo",
}


def scan_repository(repository_path):
    """Scan a local directory and return a safe file inventory with organization analysis."""
    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Expected a directory: {root}")

    files = []

    for current_directory, directories, filenames in os.walk(root):
        current_path = Path(current_directory)

        directories[:] = sorted(
            directory for directory in directories if directory not in IGNORED_DIRECTORIES
        )

        for filename in filenames:
            path = current_path / filename

            if filename in IGNORED_FILES or filename.endswith(tuple(IGNORED_SUFFIXES)):
                continue

            if filename.startswith(".env.") or path.suffix.lower() in {".pem", ".key"}:
                continue

            relative_path = path.relative_to(root)
            files.append(relative_path.as_posix())

    files.sort()

    organization_analysis = analyze_organization(files, repo_name=root.name)

    return {
        "repository_path": str(root),
        "total_files": len(files),
        "files": files,
        "organization": organization_analysis,
    }
