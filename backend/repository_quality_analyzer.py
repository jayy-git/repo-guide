from pathlib import Path

from backend.repository_analyzer import scan_repository
from backend.quality_checks import check_repository


def analyze_repository_quality(repository_path):
    """Scan a repository and return its quality findings."""

    root = Path(repository_path).resolve()

    # Scan the repository to obtain its file inventory.
    inventory = scan_repository(root)
    files = inventory["files"]

    # Normalize paths so Windows and Unix paths are handled consistently.
    filenames = {
        Path(file.replace("\\", "/")).name.lower()
        for file in files
    }

    # Locate the README and read its content when available.
    readme_path = next(
        (
            root / file
            for file in files
            if Path(file).name.lower() == "readme.md"
        ),
        None,
    )

    readme_content = None

    if readme_path and readme_path.is_file():
        try:
            readme_content = readme_path.read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeError):
            readme_content = None

    # Collect the information expected by the quality checker.
    repo_data = {
        "repo_name": root.name,
        "files": files,
        "readme_exists": "readme.md" in filenames,
        "license_exists": any(
            name == "license" or name.startswith("license.")
            for name in filenames
        ),
        "contributing_exists": any(
            name in {"contributing", "contributing.md"}
            or name.startswith("contributing.")
            for name in filenames
        ),
        "requirements_files": [
            file
            for file in files
            if Path(file).name.lower() in {
                "requirements.txt",
                "pyproject.toml",
                "package.json",
                "pipfile",
                "poetry.lock",
            }
        ],
        "readme_content": readme_content,
    }

    # Run your friend's quality checker on the collected information.
    findings = check_repository(repo_data)

    return {
        "repository_name": root.name,
        "total_files": inventory["total_files"],
        "findings_count": len(findings),
        "findings": findings,
    }