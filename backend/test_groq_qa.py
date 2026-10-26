"""Unit tests for Groq Q&A without live API calls."""
import sys
import types
from pathlib import Path
from unittest.mock import Mock

from backend.groq_qa import answer_with_groq, build_repository_context


def test_missing_key_uses_existing_deterministic_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    fallback = {"question": "What?", "answer": "Fallback answer", "sources": []}
    result = answer_with_groq(tmp_path, "What?", fallback)
    assert result["answer"] == "Fallback answer"
    assert result["provider"] == "deterministic_fallback"
    assert result["llm_available"] is False


def test_groq_response_is_returned_and_context_is_bounded(monkeypatch, tmp_path):
    (tmp_path / "README.md").write_text("A small example repository", encoding="utf-8")
    (tmp_path / "app.py").write_text("API_KEY = 'gsk_abcdefghijklmnopqrstuvwxyz1234567890'\ndef greet():\n    return 'hello'\n", encoding="utf-8")
    (tmp_path / ".env").write_text("GROQ_API_KEY=should-never-be-sent", encoding="utf-8")

    completion = types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="The app defines greet() in app.py."))])
    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=Mock(return_value=completion))))
    fake_module = types.SimpleNamespace(Groq=Mock(return_value=client))
    monkeypatch.setitem(sys.modules, "groq", fake_module)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")

    context, sources = build_repository_context(tmp_path, "Explain greet function")
    assert "should-never-be-sent" not in context
    assert "gsk_abcdefghijklmnopqrstuvwxyz1234567890" not in context
    assert "REDACTED SENSITIVE VALUE" in context
    assert all(".env" not in source for source in sources)
    result = answer_with_groq(tmp_path, "Explain greet function", {"sources": []})
    assert result["answer"] == "The app defines greet() in app.py."
    assert result["provider"] == "groq"
    assert result["model"] == "test-model"
    assert "app.py" in result["sources"]


def test_groq_failure_returns_fallback_without_leaking_error(monkeypatch, tmp_path):
    fake_module = types.SimpleNamespace(Groq=Mock(side_effect=RuntimeError("secret-key-and-stack")))
    monkeypatch.setitem(sys.modules, "groq", fake_module)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    fallback = {"question": "How does auth work?", "answer": "Fallback answer", "sources": []}
    result = answer_with_groq(tmp_path, "How does auth work?", fallback)
    assert result["answer"] == "Fallback answer"
    assert "secret-key-and-stack" not in str(result)
    assert result["provider"] == "deterministic_fallback"


def test_empty_question_uses_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    fallback = {"answer": "Please enter a valid question.", "sources": []}
    result = answer_with_groq(tmp_path, "", fallback)
    assert result["answer"] == "Please enter a valid question."
