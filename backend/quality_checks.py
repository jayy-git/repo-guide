import ast
import json
import subprocess
import sys
from pathlib import Path

from backend.repository_analyzer import scan_repository


def check_repository(repo_data):
    findings = []

    if not isinstance(repo_data, dict):
        return [{
            "title": "Invalid repository data",
            "severity": "Medium",
            "category": "Input",
            "explanation": "Repository data must be provided as a dictionary.",
            "suggestion": "Provide repository data as a dictionary with the expected fields."
        }]

    raw_files = repo_data.get("files", [])
    if isinstance(raw_files, list):
        files = [name for name in raw_files if isinstance(name, str)]
        if len(files) != len(raw_files):
            findings.append({
                "title": "Invalid repository file list",
                "severity": "Medium",
                "category": "Input",
                "explanation": "The files field must contain only file path strings.",
                "suggestion": "Provide the files field as a list of file path strings."
            })
    else:
        files = []
        findings.append({
            "title": "Invalid repository file list",
            "severity": "Medium",
            "category": "Input",
            "explanation": "The files field must be a list of file path strings.",
            "suggestion": "Provide the files field as a list of file path strings."
        })

    requirements_files = repo_data.get("requirements_files", [])
    if not isinstance(requirements_files, list):
        findings.append({
            "title": "Invalid dependency file list",
            "severity": "Medium",
            "category": "Input",
            "explanation": "The requirements_files field must be a list.",
            "suggestion": "Provide requirements_files as a list of dependency file paths."
        })
        requirements_files = []

    # Check 1: README
    if not repo_data.get("readme_exists", False):
        findings.append({
            "title": "README file not found",
            "severity": "Medium",
            "category": "Documentation",
            "explanation": "Users may not understand what the project does or how to use it.",
            "suggestion": "Add a README.md explaining the project, setup, and usage."
        })

    # Check 2: License
    if not repo_data.get("license_exists", False):
        findings.append({
            "title": "License file not found",
            "severity": "Medium",
            "category": "Legal",
            "explanation": "Users may not know the terms under which they can use or modify the project.",
            "suggestion": "Consider adding an appropriate open-source license."
        })

    # Check 3: Contribution guide
    if not repo_data.get("contributing_exists", False):
        findings.append({
            "title": "CONTRIBUTING guide not found",
            "severity": "Low",
            "category": "Onboarding",
            "explanation": "New contributors may not know how to propose changes.",
            "suggestion": "Consider adding a CONTRIBUTING.md with setup and pull request instructions."
        })
    # Check 4: Dependency files
    if not requirements_files:
        findings.append({
            "title": "Dependency file not found",
            "severity": "Low",
            "category": "Setup",
            "explanation": "Users may not know which packages are needed to run the project.",
            "suggestion": "If this project uses external packages, add a requirements.txt or an appropriate dependency file."
        })

    # Check 5: Setup instructions
    readme_content = repo_data.get("readme_content")
    setup_terms = ("installation", "getting started", "setup", "how to run", "usage")
    has_setup = isinstance(readme_content, str) and any(
        term in readme_content.lower() for term in setup_terms
    )

    if isinstance(readme_content, str) and not has_setup:
        findings.append({
            "title": "Setup instructions may be missing",
            "severity": "Low",
            "category": "Onboarding",
            "explanation": "The provided README content does not appear to include setup instructions.",
            "suggestion": "Review the README and add installation and run instructions if they are missing."
        })

    # Check 6: Git ignore file
    has_gitignore = any(
        name.replace("\\", "/").rsplit("/", 1)[-1].lower() == ".gitignore"
        for name in files
    )

    if not has_gitignore:
        findings.append({
            "title": ".gitignore file not found",
            "severity": "Low",
            "category": "Configuration",
            "explanation": "Without a .gitignore file, developers may accidentally commit temporary files or local settings.",
            "suggestion": "Consider adding a .gitignore file for generated files and local-only files."
        })
    return findings


COMPLEXITY_THRESHOLD = 10
SEVERITIES = ("Critical", "High", "Medium", "Low", "Info")


def _quality_finding(
    file_path,
    line_number,
    severity,
    category,
    explanation,
    recommendation,
):
    return {
        "file_path": file_path,
        "line_number": line_number,
        "severity": severity,
        "category": category,
        "explanation": explanation,
        "recommendation": recommendation,
    }


def _quality_report(repository_path, files_analyzed, findings):
    severity_counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        severity_counts[finding["severity"]] += 1

    return {
        "repository_path": str(repository_path),
        "files_analyzed": files_analyzed,
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
            "by_severity": severity_counts,
        },
    }


def _fallback_unused_imports(root, file_paths, findings):
    """Small AST-based F401 fallback used when Ruff is unavailable."""
    for path in file_paths:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            continue
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound_name = alias.asname or alias.name.split(".")[0]
                    imported.append((bound_name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported.append((alias.asname or alias.name, node.lineno))
        used_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
        if any(isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets) for node in tree.body):
            all_node = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets))
            if all_node.value and isinstance(all_node.value, (ast.List, ast.Tuple, ast.Set)):
                used_names.update(item.value for item in all_node.value.elts if isinstance(item, ast.Constant) and isinstance(item.value, str))
        for name, line in imported:
            if name not in used_names:
                findings.append(_quality_finding(
                    path.relative_to(root).as_posix(), line, "Medium", "Lint",
                    f"F401: '{name}' imported but unused (fallback check; Ruff unavailable).",
                    "Remove the unused import or use it in the module.",
                ))


def _fallback_complexity(sources, findings):
    """Approximate cyclomatic complexity with the Python AST when Radon is unavailable."""
    branch_types = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.ExceptHandler, ast.With, ast.AsyncWith)
    for file_path, source in sources:
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, branch_types):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += max(0, len(child.values) - 1)
                elif isinstance(child, (ast.comprehension,)):
                    complexity += len(child.ifs)
            if complexity > COMPLEXITY_THRESHOLD:
                findings.append(_quality_finding(
                    file_path, node.lineno, "Medium", "Complexity",
                    f"Function '{node.name}' has approximate cyclomatic complexity {complexity}, above the threshold of {COMPLEXITY_THRESHOLD} (fallback AST estimate; Radon unavailable).",
                    "Split the function into smaller functions or simplify its branches.",
                ))


def _run_ruff(root, file_paths, findings):
    if not file_paths:
        return

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--output-format=json",
                "--",
                *[str(path) for path in file_paths],
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        findings.append(_quality_finding(
            None,
            None,
            "Low",
            "Tool",
            f"Ruff could not be started: {error}.",
            "Install Ruff in the backend environment and rerun the analysis.",
        ))
        return

    details = result.stderr.strip()
    if "No module named ruff" in details:
        _fallback_unused_imports(root, file_paths, findings)
        return

    if result.returncode not in (0, 1):
        explanation = (
            f"Ruff could not analyze the Python files: {details or 'unknown error'}"
        )
        findings.append(_quality_finding(
            None,
            None,
            "Low",
            "Tool",
            explanation,
            "Install or repair Ruff in the backend environment and rerun the analysis.",
        ))
        return

    try:
        diagnostics = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        findings.append(_quality_finding(
            None,
            None,
            "Low",
            "Tool",
            f"Ruff returned invalid JSON output: {error}.",
            "Check the Ruff installation and rerun the analysis.",
        ))
        return

    paths_by_absolute_name = {
        str(path.resolve()): path.relative_to(root).as_posix()
        for path in file_paths
    }
    for diagnostic in diagnostics:
        absolute_name = str(Path(diagnostic["filename"]).resolve())
        relative_path = paths_by_absolute_name.get(
            absolute_name,
            Path(diagnostic["filename"]).name,
        )
        code = diagnostic.get("code") or "lint"
        line_number = diagnostic.get("location", {}).get("row")
        message = diagnostic.get("message", "Ruff reported a lint issue.")
        if code == "F401":
            recommendation = "Remove the unused import or use it in the module."
        else:
            recommendation = (
                "Apply Ruff's suggested fix when available, or update the code "
                "to follow the reported lint rule."
            )
        findings.append(_quality_finding(
            relative_path,
            line_number,
            "Medium",
            "Lint",
            f"{code}: {message}",
            recommendation,
        ))


def _check_complexity(sources, findings):
    if not sources:
        return

    try:
        from radon.complexity import cc_visit
        from radon.visitors import Function
    except ImportError:
        _fallback_complexity(sources, findings)
        return

    for file_path, source in sources:
        for block in cc_visit(source):
            if isinstance(block, Function) and block.complexity > COMPLEXITY_THRESHOLD:
                findings.append(_quality_finding(
                    file_path,
                    block.lineno,
                    "Medium",
                    "Complexity",
                    (
                        f"Function '{block.name}' has cyclomatic complexity "
                        f"{block.complexity}, above the threshold of "
                        f"{COMPLEXITY_THRESHOLD}."
                    ),
                    "Split the function into smaller functions or simplify its branches.",
                ))


def analyze_code_quality(repository_path):
    """Return Python syntax, Ruff lint, and Radon complexity findings."""
    try:
        root = Path(repository_path).resolve()
        inventory = scan_repository(root)
    except (FileNotFoundError, NotADirectoryError, TypeError, OSError, RuntimeError) as error:
        finding = _quality_finding(
            None,
            None,
            "High",
            "Input",
            f"The repository path could not be analyzed: {error}.",
            "Provide a path to an existing, accessible repository directory.",
        )
        return _quality_report(repository_path, 0, [finding])

    python_paths = [
        root / Path(file_path)
        for file_path in inventory["files"]
        if file_path.lower().endswith(".py")
    ]
    findings = []
    readable_sources = []

    for path in python_paths:
        relative_path = path.relative_to(root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            findings.append(_quality_finding(
                relative_path,
                None,
                "High",
                "Input",
                f"The Python file could not be read as UTF-8: {error}.",
                "Ensure the file is readable and saved using UTF-8 encoding.",
            ))
            continue

        try:
            ast.parse(source, filename=relative_path)
        except SyntaxError as error:
            findings.append(_quality_finding(
                relative_path,
                error.lineno,
                "Critical",
                "Syntax",
                error.msg,
                "Correct the syntax at the reported line, then rerun the analysis.",
            ))
            continue

        readable_sources.append((relative_path, source))

    _run_ruff(root, [root / path for path, _ in readable_sources], findings)
    _check_complexity(readable_sources, findings)

    return _quality_report(root, len(python_paths), findings)