"""
bug_analyzer.py
===============
Role: Backend Bug-Detection and Code-Improvement Engine
Project: RepoGuide

Analyzes Python source code using AST (Abstract Syntax Tree) static analysis
without executing untrusted code. Detects confirmed syntax errors, bug risks,
resource leaks, improper exception handling, and anti-patterns.

Generates validated, non-destructive proposed fixes and provides optional
AI-assisted explanations if an API key is configured.
"""

import ast
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.error
import urllib.parse
import urllib.request
from backend.javascript_analyzer import analyze_javascript_repository

from backend.repository_analyzer import scan_repository

logger = logging.getLogger(__name__)

# Built-in names that should not typically be shadowed as variable names
DANGEROUS_BUILTIN_SHADOWS: Set[str] = {
"list", "dict", "set", "str", "int", "id", "type",
"sum", "min", "max", "input", "format", "open",
}


# =====================================================================
# 1. SYNTAX VALIDATION & SAFE PARSING
# =====================================================================

def validate_python_syntax(code_string: str) -> Tuple[bool, Optional[str]]:
    """
    Validates Python code syntax without executing it.
    Returns (True, None) if valid, or (False, error_message) if invalid.
    """
    if not isinstance(code_string, str):
        return False, "Input must be a string."
    try:
        ast.parse(code_string)
        return True, None
    except SyntaxError as exc:
        return False, f"SyntaxError on line {exc.lineno}: {exc.msg}"
    except Exception as exc:
        return False, f"Parsing error: {str(exc)}"


def _get_evidence_snippet(lines: List[str], lineno: Optional[int], window: int = 1) -> str:
    """Extracts the offending source line safely from the lines list."""
    if not lineno or not lines or lineno < 1 or lineno > len(lines):
        return ""
    start = max(0, lineno - 1)
    end = min(len(lines), lineno + window - 1)
    return "\n".join(lines[start:end]).strip()


# =====================================================================
# 2. AST VISITOR FOR BUG DETECTION
# =====================================================================

class CodeBugVisitor(ast.NodeVisitor):
    """
    Walks the Python Abstract Syntax Tree (AST) to detect potential bugs,
    anti-patterns, and code smells. Never executes code.
    """

    def __init__(self, filename: str, source_lines: List[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.findings: List[Dict[str, Any]] = []
        # Track whether current scope is inside a with statement for open() detection
        self._inside_with_open = False

    def _add_finding(
        self,
        node: ast.AST,
        title: str,
        severity: str,
        category: str,
        explanation: str,
        proposed_fix: Optional[str] = None,
        is_potential: bool = True,
    ):
        lineno = getattr(node, "lineno", 1)
        col_offset = getattr(node, "col_offset", 0)
        evidence = _get_evidence_snippet(self.source_lines, lineno)

        self.findings.append({
            "file": self.filename,
            "line": lineno,
            "column": col_offset,
            "title": title,
            "severity": severity,
            "category": category,
            "evidence": evidence,
            "explanation": explanation,
            "proposed_fix": proposed_fix or "",
            "is_potential": is_potential,
        })

    # Rule 1: Mutable Default Arguments (def foo(x=[]))
    def _check_default_arg(self, arg_node: ast.AST, func_name: str):
        if isinstance(arg_node, (ast.List, ast.Dict, ast.Set)):
            mut_type = type(arg_node).__name__.lower().replace("def", "")
            self._add_finding(
                node=arg_node,
                title=f"Mutable default argument ({mut_type}) in function '{func_name}'",
                severity="Medium",
                category="Bug Risk",
                explanation=(
                    f"Default argument in '{func_name}' uses a mutable {mut_type}. "
                    "Python evaluates default argument expressions once at function definition time, "
                    "causing changes to persist across all subsequent function calls."
                ),
                proposed_fix=(
                    f"Use 'None' as the default argument value and initialize inside '{func_name}':\n"
                    f"if param is None:\n"
                    f"    param = {ast.unparse(arg_node) if hasattr(ast, 'unparse') else '[]'}"
                ),
                is_potential=True,
            )
        elif isinstance(arg_node, ast.Call):
            # Checking list(), dict(), set() constructor calls
            if isinstance(arg_node.func, ast.Name) and arg_node.func.id in ("list", "dict", "set"):
                self._add_finding(
                    node=arg_node,
                    title=f"Mutable default argument call '{arg_node.func.id}()' in function '{func_name}'",
                    severity="Medium",
                    category="Bug Risk",
                    explanation=(
                        f"Default argument in '{func_name}' calls mutable constructor '{arg_node.func.id}()'. "
                        "This instance is shared across every call to the function."
                    ),
                    proposed_fix=f"param=None, then: if param is None: param = {arg_node.func.id}()",
                    is_potential=True,
                )

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check positional defaults
        for default in node.args.defaults:
            self._check_default_arg(default, node.name)
        # Check keyword-only defaults
        for kw_default in getattr(node.args, "kw_defaults", []):
            if kw_default:
                self._check_default_arg(kw_default, node.name)

        # Check for unreachable code inside function body
        self._check_unreachable_code(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        for default in node.args.defaults:
            self._check_default_arg(default, node.name)
        for kw_default in getattr(node.args, "kw_defaults", []):
            if kw_default:
                self._check_default_arg(kw_default, node.name)
        self._check_unreachable_code(node.body)
        self.generic_visit(node)

    # Rule 2: Exception Handling (Bare except & Swallowed exceptions)
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Bare except: 'except:'
        if node.type is None:
            self._add_finding(
                node=node,
                title="Bare 'except:' clause caught",
                severity="High",
                category="Error Handling",
                explanation=(
                    "A bare 'except:' catches all exceptions, including KeyboardInterrupt, SystemExit, "
                    "and GeneratorExit. This makes the program difficult to interrupt and masks unexpected bugs."
                ),
                proposed_fix="except Exception as e:  # Catch standard errors rather than base exceptions",
                is_potential=True,
            )
        else:
            # Swallowed exception: 'except Exception: pass'
            is_broad = False
            if isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                is_broad = True

            # Inspect handler body
            if is_broad and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                self._add_finding(
                    node=node,
                    title="Swallowed exception with 'pass'",
                    severity="Medium",
                    category="Error Handling",
                    explanation=(
                        f"The '{ast.unparse(node.type) if hasattr(ast, 'unparse') else 'Exception'}' handler "
                        "silently ignores errors with 'pass'. This conceals failures and hinders troubleshooting."
                    ),
                    proposed_fix=(
                        "except Exception as error:\n"
                        "    logging.exception('Unexpected error: %s', error)\n"
                        "    raise"
                    ),
                    is_potential=True,
                )
        self.generic_visit(node)

    # Rule 3: None Comparison with == or != instead of 'is' / 'is not'
    def visit_Compare(self, node: ast.Compare):
        has_none = False
        if isinstance(node.left, ast.Constant) and node.left.value is None:
            has_none = True
        for comp in node.comparators:
            if isinstance(comp, ast.Constant) and comp.value is None:
                has_none = True

        if has_none:
            for op in node.ops:
                if isinstance(op, ast.Eq):
                    self._add_finding(
                        node=node,
                        title="Comparison to None using '==' instead of 'is'",
                        severity="Low",
                        category="Code Style",
                        explanation=(
                            "PEP 8 recommends using 'is None' instead of '== None'. "
                            "Classes can override '__eq__' and cause unexpected or erroneous evaluation."
                        ),
                        proposed_fix=(
                            f"{ast.unparse(node).replace(' == None', ' is None').replace('None == ', 'None is ') if hasattr(ast, 'unparse') else 'x is None'}"
                        ),
                        is_potential=True,
                    )
                elif isinstance(op, ast.NotEq):
                    self._add_finding(
                        node=node,
                        title="Comparison to None using '!=' instead of 'is not'",
                        severity="Low",
                        category="Code Style",
                        explanation=(
                            "PEP 8 recommends using 'is not None' instead of '!= None'. "
                            "Identity checks with 'is not' are faster and immune to overloaded '__eq__'."
                        ),
                        proposed_fix=(
                            f"{ast.unparse(node).replace(' != None', ' is not None').replace('None != ', 'None is not ') if hasattr(ast, 'unparse') else 'x is not None'}"
                        ),
                        is_potential=True,
                    )
        self.generic_visit(node)

    # Rule 4: Resource Leak — open() called without with statement
    def visit_With(self, node: ast.With):
        self._inside_with_open = True
        self.generic_visit(node)
        self._inside_with_open = False

    def visit_AsyncWith(self, node: ast.AsyncWith):
        self._inside_with_open = True
        self.generic_visit(node)
        self._inside_with_open = False

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            if not self._inside_with_open:
                self._add_finding(
                    node=node,
                    title="Unmanaged resource: 'open()' called outside 'with' statement",
                    severity="High",
                    category="Resource Leak",
                    explanation=(
                        "Calling 'open()' without a 'with' context manager risks leaving file descriptors open "
                        "if an exception occurs before '.close()' is reached, leading to resource exhaustion."
                    ),
                    proposed_fix=(
                        f"with open(...) as file:\n"
                        f"    data = file.read()"
                    ),
                    is_potential=True,
                )
        self.generic_visit(node)

    # Rule 5: Shadowing Critical Python Built-ins
    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in DANGEROUS_BUILTIN_SHADOWS:
                self._add_finding(
                    node=node,
                    title=f"Variable shadows built-in '{target.id}'",
                    severity="Low",
                    category="Code Style",
                    explanation=(
                        f"Assigning to variable name '{target.id}' shadows Python's built-in '{target.id}' function/type, "
                        "which can lead to TypeError if that built-in is called later in scope."
                    ),
                    proposed_fix=f"Rename '{target.id}' to '{target.id}_var' or a more descriptive domain name.",
                    is_potential=True,
                )
        self.generic_visit(node)

    # Rule 6: Unreachable Code
    def _check_unreachable_code(self, statements: List[ast.stmt]):
        terminal_nodes = (ast.Return, ast.Raise, ast.Break, ast.Continue)
        for idx, stmt in enumerate(statements[:-1]):
            if isinstance(stmt, terminal_nodes):
                next_stmt = statements[idx + 1]
                self._add_finding(
                    node=next_stmt,
                    title=f"Unreachable code detected after '{type(stmt).__name__.lower()}'",
                    severity="Medium",
                    category="Bug Risk",
                    explanation=(
                        f"Statements following '{type(stmt).__name__.lower()}' on line {getattr(stmt, 'lineno', '?')} "
                        "will never be executed."
                    ),
                    proposed_fix="Remove or relocate dead code that sits after the return/raise/break statement.",
                    is_potential=True,
                )
                break


# =====================================================================
# 3. OPTIONAL AI ENRICHMENT (SAFE FALLBACK)
# =====================================================================

def query_ai_for_explanation(finding: Dict[str, Any], timeout_seconds: int = 6) -> Optional[str]:
    """
    Queries a configured AI provider (e.g. Gemini) for enhanced context if an API key exists.
    If no key is configured or network is unavailable, returns None cleanly with NO errors.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return None

    prompt = (
        f"Explain this Python code issue and suggest a fix:\n"
        f"Title: {finding.get('title')}\n"
        f"Code: {finding.get('evidence')}\n"
        f"Please provide a 2-3 sentence explanation and safe corrected code."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key.strip()}"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return text.strip() or None
    except Exception as exc:
        logger.debug("AI explanation query skipped or failed: %s", exc)
        return None

    return None


# =====================================================================
# 4. SINGLE FILE / SNIPPET ANALYSIS ENGINE
# =====================================================================

def analyze_python_code(
    code_string: str,
    filename: str = "<source>",
    include_ai_explanations: bool = False
) -> Dict[str, Any]:
    """
    Analyzes Python source code using AST. Safe, purely static analysis.
    Returns findings structured according to the team contract.
    """
    if not isinstance(code_string, str):
        return {
            "filename": filename,
            "total_lines": 0,
            "findings_count": 1,
            "findings": [{
                "file": filename,
                "line": 1,
                "column": 0,
                "title": "Invalid source code input",
                "severity": "Medium",
                "category": "Input",
                "evidence": "",
                "explanation": "Expected source code as a text string.",
                "proposed_fix": "",
                "is_potential": False,
            }],
            "error": "Source code must be a string."
        }

    lines = code_string.splitlines()
    total_lines = len(lines)

    # Empty file handling
    if not code_string.strip():
        return {
            "filename": filename,
            "total_lines": total_lines,
            "findings_count": 0,
            "findings": [],
            "error": None
        }

    # Step 1: Parse AST & check for syntax errors
    try:
        tree = ast.parse(code_string, filename=filename)
    except SyntaxError as syntax_err:
        lineno = syntax_err.lineno or 1
        col_offset = syntax_err.offset or 0
        evidence = syntax_err.text.strip() if syntax_err.text else _get_evidence_snippet(lines, lineno)

        finding = {
            "file": filename,
            "line": lineno,
            "column": col_offset,
            "title": f"Syntax Error: {syntax_err.msg}",
            "severity": "Critical",
            "category": "Syntax",
            "evidence": evidence,
            "explanation": f"Python cannot compile this file due to a syntax error: {syntax_err.msg}.",
            "proposed_fix": "Fix syntax at the indicated line and column.",
            "is_potential": False,
        }
        return {
            "filename": filename,
            "total_lines": total_lines,
            "findings_count": 1,
            "findings": [finding],
            "error": None
        }
    except Exception as exc:
        return {
            "filename": filename,
            "total_lines": total_lines,
            "findings_count": 0,
            "findings": [],
            "error": f"Failed to parse source: {str(exc)}"
        }

    # Step 2: Traverse AST with visitor
    visitor = CodeBugVisitor(filename=filename, source_lines=lines)
    visitor.visit(tree)

    # Step 3: Optional AI enrichment
    if include_ai_explanations and os.environ.get("GEMINI_API_KEY"):
        for finding in visitor.findings:
            ai_exp = query_ai_for_explanation(finding)
            if ai_exp:
                finding["ai_explanation"] = ai_exp

    return {
        "filename": filename,
        "total_lines": total_lines,
        "findings_count": len(visitor.findings),
        "findings": visitor.findings,
        "error": None
    }


# =====================================================================
# 5. REPOSITORY-WIDE BUG SCANNER
# =====================================================================

def calculate_code_health_score(findings: List[Dict[str, Any]], total_files: int) -> int:
    """
    Calculates a repository code quality score (0 - 100).
    Penalizes according to finding severity.
    """
    if total_files == 0:
        return None

    deductions = 0
    for finding in findings:
        sev = finding.get("severity", "Low")
        if sev == "Critical":
            deductions += 20
        elif sev == "High":
            deductions += 10
        elif sev == "Medium":
            deductions += 5
        elif sev == "Low":
            deductions += 2

    # Scale score nicely
    score = max(0, 100 - deductions)
    return score


def analyze_repository_bugs(
    repository_path: str,
    include_ai_explanations: bool = False
) -> Dict[str, Any]:
    """
    Scans all Python files in a repository directory for bugs and anti-patterns.
    Reuses existing 'scan_repository' to respect ignored directories (.git, node_modules, etc.).
    """
    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Expected a directory: {root}")

    # Step 1: Discover all repository files using teammate's scan_repository
    inventory = scan_repository(root)
    all_files = inventory.get("files", [])

    # Step 2: Filter for Python source files
    py_files = [f for f in all_files if f.endswith(".py")]

    total_python_lines = 0
    all_findings: List[Dict[str, Any]] = []
    analyzed_files: List[str] = []
    file_summaries: Dict[str, int] = {}
    severity_breakdown = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}

    for rel_path in py_files:
        abs_path = root / rel_path
        if not abs_path.is_file():
            continue

        try:
            content = abs_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = abs_path.read_text(encoding="latin-1")
            except Exception:
                continue
        except Exception:
            continue

        file_res = analyze_python_code(
            code_string=content,
            filename=rel_path,
            include_ai_explanations=include_ai_explanations
        )

        total_python_lines += file_res["total_lines"]
        analyzed_files.append(rel_path)
        file_findings = file_res.get("findings", [])
        all_findings.extend(file_findings)
        file_summaries[rel_path] = len(file_findings)

        for f in file_findings:
            sev = f.get("severity", "Low")
            if sev in severity_breakdown:
                severity_breakdown[sev] += 1

        # Analyze JavaScript and TypeScript files separately.
    js_results = analyze_javascript_repository(str(root))
    js_findings = js_results.get("javascript_findings", [])

    # Combine findings from both analyzers.
    combined_findings = all_findings + js_findings

    combined_severity_breakdown = {
        "Critical": 0,
        "High": 0,
        "Medium": 0,
        "Low": 0,
        "Info": 0,
    }

    for finding in combined_findings:
        severity = finding.get("severity", "Low")
        if severity in combined_severity_breakdown:
            combined_severity_breakdown[severity] += 1

    total_analyzed_files = len(analyzed_files) + js_results.get(
        "total_javascript_files", 0
    )

    health_score = (
        calculate_code_health_score(combined_findings, total_analyzed_files)
        if total_analyzed_files > 0
        else None
    )

    return {
        "repository_name": root.name,
        "repository_path": str(root),

        # Python analysis
        "total_python_files": len(analyzed_files),
        "total_python_lines": total_python_lines,

        # JavaScript and TypeScript analysis
        "total_javascript_files": js_results.get("total_javascript_files", 0),
        "total_javascript_lines": js_results.get("total_javascript_lines", 0),
        "javascript_files_analyzed": js_results.get(
            "javascript_files_analyzed", []
        ),
        "javascript_scan_status": js_results.get(
            "javascript_scan_status", "unknown"
        ),

        # Combined analysis
        "total_analyzed_files": total_analyzed_files,
        "total_findings": len(combined_findings),
        "health_score": health_score,
        "severity_breakdown": combined_severity_breakdown,
        "file_summaries": {
            **file_summaries,
            **{
                path: sum(
                    1 for finding in js_findings
                    if finding.get("file") == path
                )
                for path in js_results.get("javascript_files_analyzed", [])
            },
        },
        "findings": combined_findings,
    }


# =====================================================================
# 6. REPORT GENERATOR (FOR "DOWNLOAD REPORT" FEATURE)
# =====================================================================

def generate_bug_report_markdown(analysis_results: Dict[str, Any]) -> str:
    """Generate a structured Markdown report of bug findings."""
    repo_name = analysis_results.get("repository_name", "Python Project")
    health = analysis_results.get("health_score")
    health_display = f"{health}/100" if health is not None else "N/A (no Python files analyzed)"
    total_findings = analysis_results.get("total_findings", 0)
    py_files = analysis_results.get("total_python_files", 0)
    py_lines = analysis_results.get("total_python_lines", 0)
    js_files = analysis_results.get("total_javascript_files", 0)
    js_lines = analysis_results.get("total_javascript_lines", 0)
    js_status = analysis_results.get("javascript_scan_status", "not_run")
    total_analyzed = analysis_results.get(
        "total_analyzed_files", py_files + js_files
    )
    breakdown = analysis_results.get("severity_breakdown", {})
    findings = analysis_results.get("findings", [])

    lines = [
        "# RepoGuide - Code Quality & Bug Detection Report",
        "",
        f"**Repository:** `{repo_name}`  ",
        f"**Code Health Score:** `{health_display}`  ",
        f"**Python Files Analyzed:** `{py_files}` ({py_lines:,} lines of code)  ",
        f"**JavaScript/TypeScript Files Analyzed:** `{js_files}` ({js_lines:,} lines of code)  ",
        f"**JavaScript/TypeScript Scan Status:** `{js_status}`  ",
        f"**Total Findings:** `{total_findings}`  ",
        "",
        "## Severity Breakdown",
        "",
        f"- **Critical (Syntax Errors):** {breakdown.get('Critical', 0)}",
        f"- **High (Resource Leaks & Bare Except):** {breakdown.get('High', 0)}",
        f"- **Medium (Mutable Defaults & Swallowed Errors):** {breakdown.get('Medium', 0)}",
        f"- **Low / Code Style (PEP 8 & Builtins):** {breakdown.get('Low', 0)}",
        "",
        "## Scoring System & Severity Guide",
        "",
       "| Severity | Penalty | Description |",
       "| :--- | :---: | :--- |",
       "| **Critical** | **-20 pts** | Critical issues identified by the applicable analyzer. |",
       "| **High** | **-10 pts** | High-priority findings that warrant prompt review. |",
       "| **Medium** | **-5 pts** | Potential bugs or maintainability concerns. |",
       "| **Low** | **-2 pts** | Lower-priority code-quality or style findings. |",
        "",
        "---",
        "",
        "## Detailed Findings",
        "",
    ]

    if total_analyzed == 0:
        lines.append(
            "**No supported source files were analyzed. "
            "This report does not establish that the repository is bug-free.**"
        )
    elif not findings:
        lines.append(
            "**No findings were reported for the analyzed source files. "
            "This does not guarantee that the repository is bug-free.**"
        )
    else:
        severity_icons = {
            "Critical": "[CRITICAL]",
            "High": "[HIGH]",
            "Medium": "[MEDIUM]",
            "Low": "[LOW]",
            "Info": "[INFO]",
        }

        for idx, finding in enumerate(findings, 1):
            severity = finding.get("severity", "Unknown")
            sev_icon = severity_icons.get(severity, "[INFO]")
            filename = finding.get("file", "unknown")
            extension = Path(filename).suffix.lower()

            language = (
                "python" if extension == ".py"
                else "typescript" if extension in {".ts", ".tsx", ".mts", ".cts"}
                else "javascript" if extension in {".js", ".jsx", ".mjs", ".cjs"}
                else ""
            )

            code_fence = language or "text"

            confirmed_error = (
                "No (Heuristic / Potential)"
                if finding.get("is_potential")
                else "Yes (Reported by analyzer)"
            )

            lines.extend([
                f"### {idx}. {sev_icon} [{severity}] "
                f"{finding.get('title', 'Untitled finding')}",
                "",
                f"- **Location:** `{filename}:{finding.get('line', '?')}` "
                f"(col {finding.get('column', '?')})",
                f"- **Category:** `{finding.get('category', 'Uncategorized')}`",
                f"- **Confirmed Error:** `{confirmed_error}`",
                "",
                "**Offending Code / Rule:**",
                f"```{code_fence}",
                finding.get("evidence") or "# Evidence unavailable",
                "```",
                "",
                "**Explanation:**",
                finding.get("explanation", ""),
                "",
            ])

            proposed_fix = finding.get("proposed_fix")
            if proposed_fix:
                lines.extend([
                    "**Suggested Fix:**",
                    f"```{code_fence}",
                    proposed_fix,
                    "```",
                    "",
                ])

            lines.extend(["---", ""])

        lines.extend([
        "## Recommended Next Steps",
        "",
        "1. Review Critical and High severity findings first.",
        "2. Inspect each finding in its reported file and line.",
        "3. Review suggested fixes before applying them.",
        "4. Run the repository's tests after making changes.",
        "",
    ])

    if js_files and js_status != "completed":
        lines.extend([
            "**Note:** JavaScript/TypeScript analysis did not complete successfully. "
            "The absence of findings from that scanner must not be interpreted as a clean scan.",
            "",
        ])

    lines.append("*Generated automatically by RepoGuide Bug-Detection Engine.*")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Scanning '{target}' for Python code bugs...")
    target_path = Path(target).resolve()
    try:
        if target_path.is_file():
            content = target_path.read_text(encoding="utf-8")
            res = analyze_python_code(content, filename=target_path.name)
            score = calculate_code_health_score(res["findings"], 1)
            print(f"Health Score: {score}/100")
            print(f"Total Lines: {res['total_lines']}")
            print(f"Total Findings: {res['findings_count']}")
            if res["findings"]:
                print("\nFindings Detected:")
                for f in res["findings"]:
                    print(f"  * [{f['severity']}] Line {f['line']}: {f['title']}")
                    if f["evidence"]:
                        print(f"    Evidence: {f['evidence']}")
                    if f["proposed_fix"]:
                        print(f"    Suggested Fix: {f['proposed_fix']}")
                    print()
            else:
                print("\nClean file! No bugs detected.")
        else:
            results = analyze_repository_bugs(target)
            print(f"Health Score: {results['health_score']}/100")
            print(f"Python Files Analyzed: {results['total_python_files']} ({results['total_python_lines']} lines)")
            print(f"Total Findings: {results['total_findings']}")
            print(f"Severity Breakdown: {results['severity_breakdown']}")
            if results["findings"]:
                print("\nFindings Detected:")
                for f in results["findings"]:
                    print(f"  * [{f['severity']}] {f['file']}:{f['line']} -> {f['title']}")
                    if f["evidence"]:
                        print(f"    Evidence: {f['evidence']}")
                    if f["proposed_fix"]:
                        print(f"    Suggested Fix: {f['proposed_fix']}")
                    print()
            else:
                print("\nClean repository! No bugs detected.")
    except Exception as exc:
        print(f"Error scanning '{target}': {exc}")


