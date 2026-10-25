
import json
import subprocess
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx", ".mts", ".cts",
}

IGNORED_DIRECTORIES = {
    "node_modules", ".git", "dist", "build",
    "coverage", ".next", ".venv", "venv",
}


def analyze_javascript_repository(repository_path: str) -> dict[str, Any]:
    """Run ESLint on JavaScript and TypeScript files without executing repository code."""

    root = Path(repository_path).resolve()

    if not root.is_dir():
        raise NotADirectoryError(f"Expected a directory: {root}")

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    eslint_bin = frontend_dir / "node_modules" / ".bin" / "eslint.cmd"

    config_prefixes = (
        "postcss.config.",
        "prettier.config.",
        "tailwind.config.",
        "vite.config.",
        "webpack.config.",
        "babel.config.",
        "jest.config.",
        "eslint.config.",
        "rollup.config.",
    )

    source_files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and not any(
            part.lower() in IGNORED_DIRECTORIES
            for part in path.relative_to(root).parts
        )
        and not path.name.lower().startswith(".eslintrc")
        and not path.name.lower().startswith(config_prefixes)
    )

    empty_result = {
        "total_javascript_files": 0,
        "total_javascript_lines": 0,
        "javascript_findings": [],
        "javascript_files_analyzed": [],
        "javascript_scan_status": "no_supported_files",
    }

    if not source_files:
        return empty_result

    if not eslint_bin.is_file():
        return {
            **empty_result,
            "javascript_scan_status": "eslint_unavailable",
        }

    # Always use RepoGuide's known flat config. External repositories may have
    # legacy .eslintrc files that ESLint 10 cannot load as flat configs.
    config_file = frontend_dir / "eslint.config.js"
    if not config_file.is_file():
        return {**empty_result, "javascript_scan_status": "eslint_config_unavailable"}

    findings: list[dict[str, Any]] = []
    analyzed_files: list[str] = []
    failed_files: list[str] = []

    for source_file in source_files:
        relative_path = source_file.relative_to(root).as_posix()

        command = [
            str(eslint_bin),
            "--format",
            "json",
        ]

        # Do not load configuration from the repository being scanned.
        # This makes scans deterministic and avoids legacy config incompatibility.
        command.extend([
            "--no-config-lookup",
            "--config",
            str(config_file),
            "--no-ignore",
        ])

        command.append(relative_path)

        try:
            result = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
                check=False,
            )

        except (OSError, subprocess.TimeoutExpired):
            failed_files.append(relative_path)
            continue

        try:
            output = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            failed_files.append(relative_path)
            continue

        if not isinstance(output, list) or not output:
            failed_files.append(relative_path)
            continue

        file_result = output[0]

        if file_result.get("fatalErrorCount", 0) > 0:
            failed_files.append(relative_path)
            continue

        analyzed_files.append(relative_path)

        for message in file_result.get("messages", []):
            # Configuration and parsing errors are not code findings.
            if message.get("fatal") or message.get("ruleId") is None:
                continue

            rule_id = message.get("ruleId")
            message_text = message.get("message", "ESLint finding")

            # ESLint's numeric severity (error/warning) describes rule configuration,
            # not the real-world risk. Map common maintainability/style rules to Low,
            # other non-fatal lint findings to Medium, and reserve High for explicitly
            # security/correctness-critical rule families.
            normalized_rule = str(rule_id).lower()
            high_risk_prefixes = (
                "security/",
                "no-unsafe-",
                "no-eval",
                "no-implied-eval",
                "no-new-func",
            )
            low_risk_rules = {
                "@typescript-eslint/no-explicit-any",
                "no-unused-vars",
                "@typescript-eslint/no-unused-vars",
                "prefer-const",
                "no-console",
                "react-refresh/only-export-components",
            }
            if normalized_rule.startswith(high_risk_prefixes):
                finding_severity = "High"
            elif normalized_rule in low_risk_rules:
                finding_severity = "Low"
            else:
                finding_severity = "Medium"

            findings.append({
                "file": relative_path,
                "line": message.get("line") or 1,
                "column": message.get("column") or 1,
                "title": message_text,
                "severity": finding_severity,
                "category": "JavaScript/TypeScript",
                "evidence": rule_id,
                "explanation": message_text,
                "proposed_fix": (
                    "Review the ESLint message and the affected code."
                ),
                "is_potential": True,
            })

    total_lines = 0

    for source_file in source_files:
        if source_file.relative_to(root).as_posix() not in analyzed_files:
            continue

        try:
            total_lines += len(
                source_file.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
            )
        except OSError:
            pass

    if not analyzed_files:
        scan_status = "failed"
    elif failed_files:
        scan_status = "partial"
    else:
        scan_status = "completed"

    return {
        "total_javascript_files": len(analyzed_files),
        "total_javascript_lines": total_lines,
        "javascript_findings": findings,
        "javascript_files_analyzed": analyzed_files,
        "javascript_scan_status": scan_status,
        "javascript_failed_files": failed_files,
    }
