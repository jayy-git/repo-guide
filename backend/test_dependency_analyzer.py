import json
import tempfile
import unittest
from pathlib import Path

from backend.dependency_analyzer import analyze_dependencies


class TestDependencyAnalyzer(unittest.TestCase):

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

    def test_requirements_txt_dependencies(self):
        self.write_file(
            "requirements.txt",
            "fastapi==0.115.0\npymongo>=4.0\n# comment\n\n"
        )

        result = analyze_dependencies(self.root)

        self.assertEqual(len(result["python"]), 2)
        self.assertEqual(
            result["python"][0]["name"],
            "fastapi"
        )
        self.assertEqual(
            result["python"][0]["version_specifier"],
            "==0.115.0"
        )
        self.assertEqual(
            result["python"][1]["name"],
            "pymongo"
        )

    def test_package_json_dependencies(self):
        package_data = {
            "dependencies": {
                "react": "^19.0.0"
            },
            "devDependencies": {
                "vite": "^6.0.0"
            }
        }

        self.write_file(
            "frontend/package.json",
            json.dumps(package_data)
        )

        result = analyze_dependencies(self.root)

        self.assertEqual(len(result["javascript"]), 2)

        names = {
            item["name"]
            for item in result["javascript"]
        }

        self.assertEqual(names, {"react", "vite"})

    def test_pyproject_toml_dependencies(self):
        self.write_file(
            "pyproject.toml",
            """
[project]
name = "demo-project"
version = "1.0.0"
dependencies = [
    "fastapi>=0.100",
    "pymongo==4.8.0"
]
"""
        )

        result = analyze_dependencies(self.root)

        names = {
            item["name"]
            for item in result["python"]
        }

        self.assertEqual(names, {"fastapi", "pymongo"})

    def test_missing_manifest_files(self):
        result = analyze_dependencies(self.root)

        self.assertEqual(result["python"], [])
        self.assertEqual(result["javascript"], [])
        self.assertEqual(result["manifest_files"], [])
        self.assertEqual(result["warnings"], [])

    def test_invalid_package_json_is_reported(self):
        self.write_file(
            "package.json",
            "{ invalid json"
        )

        result = analyze_dependencies(self.root)

        self.assertEqual(result["javascript"], [])
        self.assertTrue(result["warnings"])
        self.assertIn(
            "package.json",
            result["warnings"][0]
        )

    def test_node_modules_is_ignored(self):
        self.write_file(
            "node_modules/example/package.json",
            json.dumps({
                "dependencies": {
                    "fake-package": "1.0.0"
                }
            })
        )

        result = analyze_dependencies(self.root)

        self.assertEqual(result["javascript"], [])
        self.assertEqual(result["manifest_files"], [])

    def test_manifest_paths_are_reported(self):
        self.write_file(
            "backend/requirements.txt",
            "fastapi\n"
        )
        self.write_file(
            "frontend/package.json",
            json.dumps({
                "dependencies": {
                    "react": "^19.0.0"
                }
            })
        )

        result = analyze_dependencies(self.root)

        self.assertIn(
            "backend/requirements.txt",
            result["manifest_files"]
        )
        self.assertIn(
            "frontend/package.json",
            result["manifest_files"]
        )

    def test_invalid_repository_path(self):
        missing_path = self.root / "does-not-exist"

        with self.assertRaises(FileNotFoundError):
            analyze_dependencies(missing_path)


if __name__ == "__main__":
    unittest.main()