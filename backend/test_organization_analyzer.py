"""
test_organization_analyzer.py
=============================
Test suite verifying all 8 organization and structure analysis capabilities:
1. Directory analysis
2. File classification
3. Project convention detection
4. Organisation issue detection
5. Folder structure recommendations
6. Dependency and configuration review
7. Change planning
8. Organisation report
"""

import unittest
from pathlib import Path
from backend.organization_analyzer import (
    analyze_directories,
    classify_files,
    detect_project_conventions,
    detect_organization_issues,
    recommend_folder_structure,
    review_dependencies_and_config,
    plan_organization_changes,
    generate_organization_report,
    analyze_organization
)


class TestOrganizationAnalyzer(unittest.TestCase):

    def setUp(self):
        # A realistic sample project file list with common organizational patterns and issues
        self.sample_files = [
            ".gitignore",
            "README.md",
            "backend/main.py",
            "backend/models.py",
            "backend/requirements.txt",
            "backend/test_main.py",  # Note: Test placed alongside source (misplaced test issue)
            "frontend/package.json",
            "frontend/index.html",
            "frontend/src/App.jsx",
            "frontend/src/index.css",
            "frontend/public/logo.svg"
        ]

    # --- 1. Directory analysis ---
    def test_directory_analysis(self):
        result = analyze_directories(self.sample_files)
        self.assertIn("total_directories", result)
        self.assertIn("max_directory_depth", result)
        self.assertIn("directory_counts", result)
        self.assertIn("backend", result["directories"])
        self.assertIn("frontend/src", result["directories"])
        self.assertEqual(result["directory_counts"]["root"], 2)  # .gitignore, README.md
        print("[PASS] 1. Directory analysis verified.")

    # --- 2. File classification ---
    def test_file_classification(self):
        result = classify_files(self.sample_files)
        counts = result["counts"]
        categories = result["categories"]

        self.assertGreater(counts["source"], 0)
        self.assertIn("backend/main.py", categories["source"])
        self.assertIn("frontend/src/App.jsx", categories["source"])

        self.assertGreater(counts["tests"], 0)
        self.assertIn("backend/test_main.py", categories["tests"])

        self.assertGreater(counts["documentation"], 0)
        self.assertIn("README.md", categories["documentation"])

        self.assertGreater(counts["configuration"], 0)
        self.assertIn("backend/requirements.txt", categories["configuration"])
        self.assertIn("frontend/package.json", categories["configuration"])
        self.assertIn(".gitignore", categories["configuration"])

        self.assertGreater(counts["assets"], 0)
        self.assertIn("frontend/src/index.css", categories["assets"])
        print("[PASS] 2. File classification verified.")

    # --- 3. Project convention detection ---
    def test_project_convention_detection(self):
        classified = classify_files(self.sample_files)
        result = detect_project_conventions(self.sample_files, classified["categories"])

        self.assertEqual(result["architecture_type"], "Full-Stack Application (Frontend / Backend Split)")
        self.assertIn("FastAPI", result["detected_frameworks"])
        self.assertIn("React", result["detected_frameworks"])
        print("[PASS] 3. Project convention detection verified.")

    # --- 4. Organisation issue detection ---
    def test_organization_issue_detection(self):
        classified = classify_files(self.sample_files)
        conventions = detect_project_conventions(self.sample_files, classified["categories"])
        issues = detect_organization_issues(self.sample_files, classified["categories"], conventions)

        # Should detect misplaced test in backend/test_main.py
        issue_categories = [item["category"] for item in issues]
        self.assertIn("Test Organization", issue_categories)
        self.assertIn("Legal", issue_categories)  # Missing LICENSE
        print("[PASS] 4. Organisation issue detection verified.")

    # --- 5. Folder structure recommendations ---
    def test_folder_structure_recommendations(self):
        classified = classify_files(self.sample_files)
        conventions = detect_project_conventions(self.sample_files, classified["categories"])
        issues = detect_organization_issues(self.sample_files, classified["categories"], conventions)
        recs = recommend_folder_structure(conventions, issues)

        self.assertIn("recommended_layout", recs)
        self.assertIn("backend/", recs["recommended_layout"])
        self.assertIn("frontend/", recs["recommended_layout"])
        self.assertTrue(len(recs["rationale"]) > 0)
        print("[PASS] 5. Folder structure recommendations verified.")

    # --- 6. Dependency and configuration review ---
    def test_dependency_and_config_review(self):
        review = review_dependencies_and_config(self.sample_files)
        dep_files = [d["file"] for d in review["dependency_files"]]
        self.assertIn("backend/requirements.txt", dep_files)
        self.assertIn("frontend/package.json", dep_files)

        cfg_files = [c["file"] for c in review["configuration_files"]]
        self.assertIn(".gitignore", cfg_files)
        print("[PASS] 6. Dependency and configuration review verified.")

    # --- 7. Change planning ---
    def test_change_planning(self):
        classified = classify_files(self.sample_files)
        conventions = detect_project_conventions(self.sample_files, classified["categories"])
        issues = detect_organization_issues(self.sample_files, classified["categories"], conventions)
        plan = plan_organization_changes(self.sample_files, classified["categories"], issues)

        # Plan should propose moving backend/test_main.py -> backend/tests/test_main.py
        move_actions = [p for p in plan if p["action"] == "MOVE"]
        self.assertTrue(any("test_main.py" in m["source"] and "tests" in m["destination"] for m in move_actions))

        # Plan should propose creating LICENSE
        create_actions = [p for p in plan if p["action"] == "CREATE"]
        self.assertTrue(any(c["destination"] == "LICENSE" for c in create_actions))
        print("[PASS] 7. Change planning verified.")

    # --- 8. Organisation report ---
    def test_organization_report(self):
        org_result = analyze_organization(self.sample_files, repo_name="DemoApp")
        report = org_result["organization_report"]

        self.assertIn("# RepoGuide Repository Organization & Structure Report", report)
        self.assertIn("Executive Summary", report)
        self.assertIn("File Classification Breakdown", report)
        self.assertIn("Recommended Folder Structure", report)
        self.assertIn("Actionable Change Plan", report)
        print("[PASS] 8. Organisation report generation verified.")


if __name__ == "__main__":
    unittest.main()
