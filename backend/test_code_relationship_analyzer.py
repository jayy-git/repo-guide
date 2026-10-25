import tempfile
import unittest
from pathlib import Path

from backend.code_relationship_analyzer import analyze_code_relationships


class TestCodeRelationshipAnalyzer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_file(self, relative_path, content):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_detects_direct_import_relationship(self):
        self.write_file(
            "main.py",
            "from helper import greet\n"
        )
        self.write_file(
            "helper.py",
            "def greet():\n    return 'Hello'\n"
        )

        result = analyze_code_relationships(self.root)

        self.assertEqual(result["relationships_count"], 1)

        relationship = result["relationships"][0]

        self.assertEqual(relationship["source_file"], "main.py")
        self.assertEqual(relationship["target_file"], "helper.py")
        self.assertEqual(relationship["relationship"], "imports")

    def test_imported_by_count(self):
        self.write_file(
            "main.py",
            "import helper\n"
        )
        self.write_file(
            "another.py",
            "import helper\n"
        )
        self.write_file(
            "helper.py",
            "VALUE = 10\n"
        )

        result = analyze_code_relationships(self.root)

        self.assertEqual(
            result["imported_by_count"]["helper.py"],
            2
        )

    def test_ignores_external_imports(self):
        self.write_file(
            "main.py",
            "import json\nimport os\n"
        )

        result = analyze_code_relationships(self.root)

        self.assertEqual(result["relationships"], [])
        self.assertEqual(result["relationships_count"], 0)

    def test_ignores_virtual_environment_directories(self):
        self.write_file(
            "main.py",
            "import helper\n"
        )
        self.write_file(
            ".venv/Lib/site-packages/helper.py",
            "VALUE = 10\n"
        )

        result = analyze_code_relationships(self.root)

        self.assertEqual(result["python_files_analyzed"], 1)
        self.assertEqual(result["relationships"], [])

    def test_invalid_repository_path(self):
        missing_path = self.root / "missing"

        with self.assertRaises(FileNotFoundError):
            analyze_code_relationships(missing_path)

    def test_invalid_python_file_generates_warning(self):
        self.write_file(
            "broken.py",
            "def invalid(:\n"
        )

        result = analyze_code_relationships(self.root)

        self.assertEqual(result["python_files_analyzed"], 1)
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()