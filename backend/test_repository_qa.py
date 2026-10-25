from pathlib import Path

from backend.repository_qa import answer_repository_question


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def ask(question):
    return answer_repository_question(REPOSITORY_ROOT, question)


def test_bug_count_question_returns_count_and_source():
    result = ask("How many bugs were detected?")
    assert "finding(s)" in result["answer"]
    assert "backend/bug_analyzer.py" in result["sources"]


def test_health_score_question_returns_score():
    result = ask("What is the code health score?")
    assert "/100" in result["answer"]


def test_project_structure_uses_paths_relative_to_folder():
    result = ask("Show me the project structure.")
    assert "backend/" in result["answer"]
    assert "backend/backend/" not in result["answer"]
    assert "main.py" in result["answer"]


def test_important_files_does_not_return_import_relationships():
    result = ask("What are the important files in this repository?")
    assert "Relevant files:" in result["answer"]
    assert "imports" not in result["answer"]
    assert ".gitignore" not in result["answer"]
    assert "frontend/src/App.jsx" in result["answer"]


def test_analyzer_roles_are_distinguished():
    result = ask("Which Python files analyze code quality and detect bugs?")
    assert "repository_quality_analyzer.py" in result["answer"]
    assert "bug_analyzer.py" in result["answer"]
    assert "repository_qa.py" in result["answer"]


def test_dependency_question_lists_manifest_source():
    result = ask("List the dependencies and packages.")
    assert "Python dependencies:" in result["answer"]
    assert "JavaScript dependencies:" in result["answer"]
    assert "backend/requirements.txt" in result["sources"]
    assert "frontend/package.json" in result["sources"]


def test_empty_question_is_handled():
    result = answer_repository_question(REPOSITORY_ROOT, "   ")
    assert result["answer"] == "Please enter a valid question."
