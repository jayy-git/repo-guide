import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.quality_checks import analyze_code_quality, check_repository


class TestQualityChecks(unittest.TestCase):

    def complete_repository(self):
        return {
            "repo_name": "demo-project",
            "files": [
                "README.md",
                "LICENSE",
                "CONTRIBUTING.md",
                "requirements.txt",
                ".gitignore"
            ],
            "readme_exists": True,
            "license_exists": True,
            "contributing_exists": True,
            "requirements_files": ["requirements.txt"]
        }

    def test_missing_required_files_report_expected_findings(self):
        repo_data = {
            "files": [],
            "readme_exists": False,
            "license_exists": False,
            "contributing_exists": False,
            "requirements_files": []
        }

        findings = check_repository(repo_data)
        finding_titles = [finding["title"] for finding in findings]

        self.assertIn("README file not found", finding_titles)
        self.assertIn("License file not found", finding_titles)
        self.assertIn("CONTRIBUTING guide not found", finding_titles)
        self.assertIn("Dependency file not found", finding_titles)
        self.assertIn(".gitignore file not found", finding_titles)

    def test_all_files_present(self):
        self.assertEqual(check_repository(self.complete_repository()), [])

    def test_every_finding_has_required_fields_and_valid_severity(self):
        repo_data = {
            "files": [],
            "readme_exists": False,
            "license_exists": False,
            "contributing_exists": False,
            "requirements_files": [],
            "readme_content": "Project overview without setup details."
        }
        required_fields = {
            "title",
            "severity",
            "category",
            "explanation",
            "suggestion"
        }
        allowed_severities = {"Critical", "High", "Medium", "Low", "Info"}

        for finding in check_repository(repo_data):
            self.assertTrue(required_fields.issubset(finding.keys()))
            self.assertIn(finding["severity"], allowed_severities)

    def test_incomplete_data(self):
        findings = check_repository({"files": []})

        self.assertIsInstance(findings, list)
        finding_titles = [finding["title"] for finding in findings]
        self.assertIn("README file not found", finding_titles)
        self.assertIn("License file not found", finding_titles)
        self.assertIn("CONTRIBUTING guide not found", finding_titles)
        self.assertIn("Dependency file not found", finding_titles)

    def test_non_dictionary_input_is_handled_safely(self):
        findings = check_repository(None)

        self.assertIsInstance(findings, list)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["title"], "Invalid repository data")

    def test_incorrectly_typed_files_field_is_reported_safely(self):
        findings = check_repository({"files": "README.md"})
        finding_titles = [finding["title"] for finding in findings]

        self.assertIn("Invalid repository file list", finding_titles)
        self.assertIn(".gitignore file not found", finding_titles)

    def test_gitignore_detection_accepts_windows_and_unix_paths(self):
        for gitignore_path in (r"config\.gitignore", "config/.gitignore"):
            with self.subTest(path=gitignore_path):
                repo_data = self.complete_repository()
                repo_data["files"] = [gitignore_path]

                finding_titles = [
                    finding["title"] for finding in check_repository(repo_data)
                ]

                self.assertNotIn(".gitignore file not found", finding_titles)

    def test_setup_check_is_skipped_when_readme_content_is_unavailable(self):
        repo_data = self.complete_repository()

        finding_titles = [
            finding["title"] for finding in check_repository(repo_data)
        ]

        self.assertNotIn("Setup instructions may be missing", finding_titles)

    def test_setup_finding_requires_supplied_readme_without_setup_instructions(self):
        repo_data = self.complete_repository()
        repo_data["readme_content"] = "This README describes the project."

        finding_titles = [
            finding["title"] for finding in check_repository(repo_data)
        ]

        self.assertIn("Setup instructions may be missing", finding_titles)

    def test_setup_finding_is_not_reported_when_readme_has_setup_instructions(self):
        repo_data = self.complete_repository()
        repo_data["readme_content"] = "## Installation\nRun the application."

        finding_titles = [
            finding["title"] for finding in check_repository(repo_data)
        ]

        self.assertNotIn("Setup instructions may be missing", finding_titles)

    def test_code_quality_report_for_clean_python_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sample.py").write_text(
                'def greet(name):\n    return f"Hello, {name}"\n',
                encoding="utf-8",
            )

            report = analyze_code_quality(root)

        self.assertEqual(report["files_analyzed"], 1)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["summary"]["total_findings"], 0)

    def test_syntax_errors_include_file_path_and_line_number(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "broken.py").write_text(
                "def broken(:\n    pass\n",
                encoding="utf-8",
            )

            report = analyze_code_quality(root)

        syntax_findings = [
            finding
            for finding in report["findings"]
            if finding["category"] == "Syntax"
        ]
        self.assertEqual(len(syntax_findings), 1)
        self.assertEqual(syntax_findings[0]["file_path"], "broken.py")
        self.assertEqual(syntax_findings[0]["line_number"], 1)
        self.assertEqual(syntax_findings[0]["severity"], "Critical")
        self.assertTrue(syntax_findings[0]["recommendation"])

    def test_ruff_reports_unused_imports(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "unused.py").write_text(
                "import os\n\nvalue = 1\n",
                encoding="utf-8",
            )

            report = analyze_code_quality(root)

        lint_findings = [
            finding
            for finding in report["findings"]
            if finding["category"] == "Lint"
        ]
        self.assertTrue(any(
            finding["file_path"] == "unused.py"
            and finding["line_number"] == 1
            and "F401" in finding["explanation"]
            for finding in lint_findings
        ))

    def test_radon_reports_overly_complex_functions(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            branches = "\n".join(
                f"    if value == {number}:\n        result += {number}"
                for number in range(10)
            )
            (root / "complex.py").write_text(
                f"def too_complex(value):\n    result = 0\n{branches}\n"
                "    return result\n",
                encoding="utf-8",
            )

            report = analyze_code_quality(root)

        complexity_findings = [
            finding
            for finding in report["findings"]
            if finding["category"] == "Complexity"
        ]
        self.assertEqual(len(complexity_findings), 1)
        self.assertEqual(complexity_findings[0]["file_path"], "complex.py")
        self.assertEqual(complexity_findings[0]["line_number"], 1)
        self.assertIn("complexity 11", complexity_findings[0]["explanation"])

    def test_invalid_repository_paths_return_structured_input_findings(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "not-a-directory"
            file_path.write_text("not a directory", encoding="utf-8")

            for invalid_path in (
                file_path / "missing",
                file_path,
            ):
                with self.subTest(path=invalid_path):
                    report = analyze_code_quality(invalid_path)

                    self.assertEqual(report["files_analyzed"], 0)
                    self.assertEqual(len(report["findings"]), 1)
                    self.assertEqual(report["findings"][0]["category"], "Input")
                    self.assertIsNone(report["findings"][0]["file_path"])
                    self.assertIsNone(report["findings"][0]["line_number"])
                    self.assertTrue(report["findings"][0]["recommendation"])

    def test_missing_ruff_uses_fallback_without_aborting_analysis(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sample.py").write_text(
                "value = 1\n",
                encoding="utf-8",
            )
            missing_ruff = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="No module named ruff",
            )

            with patch(
                "backend.quality_checks.subprocess.run",
                return_value=missing_ruff,
            ):
                report = analyze_code_quality(root)

        self.assertEqual(report["files_analyzed"], 1)
        self.assertFalse(any(finding["category"] == "Tool" for finding in report["findings"]))

    def test_missing_radon_uses_fallback_without_aborting_analysis(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sample.py").write_text(
                "value = 1\n",
                encoding="utf-8",
            )

            with patch.dict(
                "sys.modules",
                {
                    "radon": None,
                    "radon.complexity": None,
                    "radon.visitors": None,
                },
            ):
                report = analyze_code_quality(root)

        self.assertEqual(report["files_analyzed"], 1)
        self.assertFalse(any(finding["category"] == "Tool" for finding in report["findings"]))


if __name__ == "__main__":
    unittest.main()