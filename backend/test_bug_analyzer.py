"""
test_bug_analyzer.py
====================
Unit tests for bug_analyzer.py in RepoGuide.
Tests AST parsing, bug pattern detection, syntax validation,
empty/invalid file handling, and repository scanning.
"""

import unittest
from pathlib import Path

from backend.bug_analyzer import (
    analyze_python_code,
    analyze_repository_bugs,
    calculate_code_health_score,
    generate_bug_report_markdown,
    validate_python_syntax,
)


class TestBugAnalyzer(unittest.TestCase):

    def test_syntax_validation(self):
        valid_code = "def add(a, b):\n    return a + b"
        is_valid, err = validate_python_syntax(valid_code)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        invalid_code = "def broken(:"
        is_valid, err = validate_python_syntax(invalid_code)
        self.assertFalse(is_valid)
        self.assertIn("SyntaxError", err)

    def test_syntax_error_reported_as_critical_finding(self):
        broken_code = "def foo(\n    print('missing paren'"
        res = analyze_python_code(broken_code, filename="broken.py")

        self.assertEqual(res["findings_count"], 1)
        finding = res["findings"][0]
        self.assertEqual(finding["severity"], "Critical")
        self.assertEqual(finding["category"], "Syntax")
        self.assertFalse(finding["is_potential"])

    def test_empty_source_code_handled_safely(self):
        res = analyze_python_code("", filename="empty.py")
        self.assertEqual(res["findings_count"], 0)
        self.assertEqual(res["findings"], [])
        self.assertIsNone(res["error"])

    def test_non_string_input_handled_gracefully(self):
        res = analyze_python_code(None, filename="invalid.py")
        self.assertGreaterEqual(res["findings_count"], 1)
        self.assertEqual(res["findings"][0]["title"], "Invalid source code input")

    def test_detect_mutable_default_arguments(self):
        code = (
            "def append_item(val, target=[]):\n"
            "    target.append(val)\n"
            "    return target\n\n"
            "def config_loader(opts={}):\n"
            "    return opts\n"
        )
        res = analyze_python_code(code, filename="defaults.py")
        titles = [f["title"] for f in res["findings"]]

        self.assertTrue(any("Mutable default argument" in t for t in titles))

    def test_detect_bare_except_and_swallowed_exceptions(self):
        code = (
            "try:\n"
            "    x = 1 / 0\n"
            "except:\n"
            "    print('error')\n\n"
            "try:\n"
            "    y = int('abc')\n"
            "except Exception:\n"
            "    pass\n"
        )
        res = analyze_python_code(code, filename="exceptions.py")
        titles = [f["title"] for f in res["findings"]]

        self.assertIn("Bare 'except:' clause caught", titles)
        self.assertIn("Swallowed exception with 'pass'", titles)

    def test_detect_comparison_to_none(self):
        code = (
            "def check_val(x):\n"
            "    if x == None:\n"
            "        return False\n"
            "    if x != None:\n"
            "        return True\n"
        )
        res = analyze_python_code(code, filename="none_comp.py")
        titles = [f["title"] for f in res["findings"]]

        self.assertIn("Comparison to None using '==' instead of 'is'", titles)
        self.assertIn("Comparison to None using '!=' instead of 'is not'", titles)

    def test_detect_unmanaged_resource_open_outside_with(self):
        leak_code = (
            "def read_file(path):\n"
            "    f = open(path)\n"
            "    data = f.read()\n"
            "    return data\n"
        )
        res = analyze_python_code(leak_code, filename="leak.py")
        titles = [f["title"] for f in res["findings"]]
        self.assertIn("Unmanaged resource: 'open()' called outside 'with' statement", titles)

        # Confirm that using 'with open(...) as f' does NOT trigger the finding
        safe_code = (
            "def read_file(path):\n"
            "    with open(path) as f:\n"
            "        return f.read()\n"
        )
        safe_res = analyze_python_code(safe_code, filename="safe.py")
        safe_titles = [f["title"] for f in safe_res["findings"]]
        self.assertNotIn("Unmanaged resource: 'open()' called outside 'with' statement", safe_titles)

    def test_detect_unreachable_code(self):
        code = (
            "def calculate(a, b):\n"
            "    return a + b\n"
            "    print('This will never run')\n"
        )
        res = analyze_python_code(code, filename="dead_code.py")
        titles = [f["title"] for f in res["findings"]]
        self.assertTrue(any("Unreachable code detected" in t for t in titles))

    def test_detect_builtin_shadowing(self):
        code = (
            "list = [1, 2, 3]\n"
            "dict = {'a': 1}\n"
        )
        res = analyze_python_code(code, filename="shadow.py")
        titles = [f["title"] for f in res["findings"]]
        self.assertIn("Variable shadows built-in 'list'", titles)
        self.assertIn("Variable shadows built-in 'dict'", titles)

    def test_file_variable_is_not_builtin_shadowing(self):
        code = (
            "def read_data(path):\n"
            "    file = open(path, 'r')\n"
            "    return file.read()\n"
        )
        res = analyze_python_code(code, filename="read_data.py")
        titles = [f["title"] for f in res["findings"]]

        self.assertNotIn("Variable shadows built-in 'file'", titles)

    def test_code_health_score_calculation(self):
        clean_score = calculate_code_health_score([], 5)
        self.assertEqual(clean_score, 100)

        dirty_findings = [
            {"severity": "Critical"},
            {"severity": "High"},
            {"severity": "Medium"},
            {"severity": "Low"},
        ]
        score = calculate_code_health_score(dirty_findings, 1)
        self.assertLess(score, 100)

    def test_scan_repository_bugs(self):
        backend_dir = Path(__file__).resolve().parent
        res = analyze_repository_bugs(str(backend_dir))

        self.assertIn("repository_name", res)
        self.assertGreater(res["total_python_files"], 0)
        self.assertIn("health_score", res)
        self.assertIn("severity_breakdown", res)
        self.assertIsInstance(res["findings"], list)

    def test_generate_bug_report_markdown(self):
        mock_results = {
            "repository_name": "DemoRepo",
            "health_score": 85,
            "total_python_files": 3,
            "total_python_lines": 120,
            "total_findings": 1,
            "severity_breakdown": {"Critical": 0, "High": 0, "Medium": 1, "Low": 0, "Info": 0},
            "findings": [{
                "file": "utils.py",
                "line": 10,
                "column": 4,
                "title": "Mutable default argument in function 'helper'",
                "severity": "Medium",
                "category": "Bug Risk",
                "evidence": "def helper(items=[]):",
                "explanation": "Default argument uses mutable list.",
                "proposed_fix": "items=None",
                "is_potential": True,
            }]
        }
        report = generate_bug_report_markdown(mock_results)
        self.assertIn("# RepoGuide - Code Quality & Bug Detection Report", report)
        self.assertIn("DemoRepo", report)
        self.assertIn("85/100", report)
        self.assertIn("utils.py:10", report)
        self.assertIn("Mutable default argument", report)


if __name__ == "__main__":
    unittest.main()

