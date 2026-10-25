import tempfile
import unittest
from pathlib import Path

from backend.documentation_validator import validate_documentation


class TestDocumentationValidator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_onboarding(self, content):
        path = self.root / "ONBOARDING.md"
        path.write_text(content, encoding="utf-8")
        return path

    def complete_documentation(self):
        return """# Project Onboarding

## 1. Project Overview
Example project.

## 2. Technology Stack
Python.

## 3. Important Files
- `backend/main.py`

## 4. Project Structure
Backend modules.

## 5. Setup Guidance
Install dependencies.

## 6. Code Relationships
- `backend/main.py` imports `backend/helper.py`
"""

    def test_valid_documentation(self):
        (self.root / "backend").mkdir()
        (self.root / "backend" / "main.py").write_text(
            "print('Hello')",
            encoding="utf-8",
        )
        (self.root / "backend" / "helper.py").write_text(
            "VALUE = 1",
            encoding="utf-8",
        )

        self.write_onboarding(self.complete_documentation())

        result = validate_documentation(self.root)

        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["warnings"], [])

    def test_missing_onboarding_document(self):
        result = validate_documentation(self.root)

        self.assertFalse(result["valid"])
        self.assertTrue(result["issues"])

    def test_empty_onboarding_document(self):
        self.write_onboarding("   ")

        result = validate_documentation(self.root)

        self.assertFalse(result["valid"])
        self.assertTrue(result["issues"])

    def test_missing_required_section(self):
        self.write_onboarding(
            """# Project Onboarding

## Project Overview
Example project.
"""
        )

        result = validate_documentation(self.root)

        self.assertFalse(result["valid"])

        issue_checks = [
            issue["check"]
            for issue in result["issues"]
        ]

        self.assertIn("required_sections", issue_checks)

    def test_referenced_file_does_not_exist(self):
        self.write_onboarding(
            self.complete_documentation()
        )

        result = validate_documentation(self.root)

        issue_checks = [
            issue["check"]
            for issue in result["issues"]
        ]

        self.assertIn("referenced_files_exist", issue_checks)

    def test_missing_code_relationships_section_produces_warning(self):
        self.write_onboarding(
            """# Project Onboarding

## Project Overview
Example project.

## Technology Stack
Python.

## Important Files
Main module.

## Project Structure
Backend.

## Setup Guidance
Install dependencies.
"""
        )

        result = validate_documentation(self.root)

        self.assertTrue(
            any(
                "Code Relationships" in warning
                for warning in result["warnings"]
            )
        )

    def test_invalid_repository_path(self):
        missing_path = self.root / "missing"

        with self.assertRaises(FileNotFoundError):
            validate_documentation(missing_path)


if __name__ == "__main__":
    unittest.main()