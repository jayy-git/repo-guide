from pathlib import Path

from backend.repository_summary import generate_repository_summary
from backend.documentation_validator import validate_documentation


def generate_onboarding_document(repository_path):
    """Generate an ONBOARDING.md document for a repository."""

    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Expected a directory: {root}"
        )

    # Get information from our existing analysis engine.
    summary = generate_repository_summary(root)

    technologies = summary["technology_stack"]
    important_files = summary["important_files"]
    dependencies = summary["dependencies"]
    code_relationships = summary["code_relationships"]

    lines = [
        f"# {summary['repository_name']} — Developer Onboarding",
        "",
        "## 1. Project Overview",
        "",
        f"This repository contains **{summary['total_files']} files** "
"identified by RepoGuide's repository scanner.",
        "",
        "This document provides an initial overview of the repository, "
        "its technology stack, important files, and setup resources.",
        "",
        "## 2. Technology Stack",
        "",
    ]

    for category, items in technologies.items():
        label = category.replace("_", " ").title()
        value = ", ".join(items) if items else "Not detected"
        lines.append(f"- **{label}:** {value}")

    lines.extend([
        "",
        "## 3. Important Files",
        "",
    ])

    for item in important_files:
        lines.append(f"### `{item['file']}`")
        lines.append("")
        lines.append(item["purpose"])
        lines.append("")

    lines.extend([
        "",
        "## 4. Dependencies",
        "",
        "### Python Dependencies",
        "",
    ])

    if dependencies["python"]:
        for dependency in dependencies["python"]:
            name = dependency["name"]
            version = dependency["version_specifier"] or "Version unspecified"
            lines.append(f"- **{name}** — `{version}`")
    else:
        lines.append("No Python dependencies detected.")

    lines.extend([
        "",
        "### JavaScript Dependencies",
        "",
    ])

    if dependencies["javascript"]:
        for dependency in dependencies["javascript"]:
            name = dependency["name"]
            version = dependency["version_specifier"] or "Version unspecified"
            dependency_type = dependency["dependency_type"]
            lines.append(
                f"- **{name}** — `{version}` ({dependency_type})"
            )
    else:
        lines.append("No JavaScript dependencies detected.")

    if dependencies["warnings"]:
        lines.extend([
            "",
            "### Dependency Analysis Warnings",
            "",
        ])
        for warning in dependencies["warnings"]:
            lines.append(f"- {warning}")

    lines.extend([
        "",
        "## 5. Project Structure",
        "",
        "The following files provide a starting point for exploring "
        "the repository:",
        "",
    ])

    for item in important_files[:15]:
        lines.append(f"- `{item['file']}`")

    lines.extend([
        "",
        "## 6. Code Relationships",
        "",
        "This section identifies relationships between Python files "
        "based on their import statements.",
        "",
    ])

    relationships = code_relationships["relationships"]

    if relationships:
        for relationship in relationships:
            lines.append(
                f"- `{relationship['source_file']}` imports "
                f"`{relationship['target_file']}`"
            )
    else:
        lines.append(
            "No internal Python import relationships were detected."
        )

    lines.extend([
        "",
        f"**Python files analyzed:** "
        f"{code_relationships['python_files_analyzed']}",
        f"**Relationships detected:** "
        f"{code_relationships['relationships_count']}",
        "",
        "## 7. Setup Guidance",
        "",
        "Use the following files to understand how to install and run "
        "the project:",
        "",
        "- `README.md` or a directory-specific README: check for "
        "project instructions.",
        "- `requirements.txt`: inspect Python dependencies.",
        "- `package.json`: inspect JavaScript dependencies and scripts.",
        "- `.env.example`: check which environment variables are required, "
        "if this file exists.",
        "",
        "Before running the project, review its README and configuration. "
        "Install only the dependencies required by the project.",
        "",
        "**Note:** This document is generated automatically. Verify the "
        "instructions and file descriptions before relying on them.",
        "",
    ])

    document_content = "\n".join(lines)

    # Write the generated document into the repository.
    output_path = root / "ONBOARDING.md"
    output_path.write_text(document_content, encoding="utf-8")


    validation = validate_documentation(root)

    return {
    "output_path": str(output_path),
    "characters_written": len(document_content),
    "repository_name": summary["repository_name"],
    "documentation_validation": validation,
}