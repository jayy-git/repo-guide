from pathlib import Path

from backend.repository_summary import generate_repository_summary
from backend.repository_quality_analyzer import analyze_repository_quality
from backend.bug_analyzer import analyze_repository_bugs


def answer_repository_question(repository_path, question):
    """Answer common questions using data extracted from a local repository."""
    root = Path(repository_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repository path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Expected a directory: {root}")
    if not isinstance(question, str) or not question.strip():
        return {"question": question, "answer": "Please enter a valid question.", "sources": []}

    q = " ".join(question.lower().strip().replace("?", " ").replace("!", " ").split())
    summary = generate_repository_summary(root)
    important_files = summary.get("important_files", [])
    technologies = summary.get("technology_stack", {})
    dependencies = summary.get("dependencies", {})
    relationships = summary.get("code_relationships", {})
    structure = summary.get("project_structure", {})
    answer, sources = "", []

    # Ask the analyzers only when the question needs their results.
    needs_bug_results = any(word in q for word in (
        "bug", "bugs", "issue", "issues", "health score", "code health", "finding", "findings", "vulnerabilit"
    ))
    bug_results = analyze_repository_bugs(str(root), include_ai_explanations=False) if needs_bug_results else {}
    needs_quality_results = any(word in q for word in ("quality check", "quality finding", "missing license", "contributing guide"))
    quality_results = analyze_repository_quality(root) if needs_quality_results else {}

    # Prioritize narrow questions before broad keyword matches.
    if any(term in q for term in ("health score", "code health", "overall quality score")):
        score = bug_results.get("health_score")
        answer = f"The current code health score is {score}/100." if score is not None else "A code health score is not available."
        sources = ["backend/bug_analyzer.py"] if (root / "backend/bug_analyzer.py").exists() else ["bug_analyzer.py"]

    elif any(term in q for term in ("how many bug", "how many issue", "bug count", "number of bug", "number of issue", "how many finding", "total finding", "detected bug", "detected issue", "any bug", "any issue", "bugs detected", "issues detected")):
        count = bug_results.get("total_findings", 0)
        breakdown = bug_results.get("severity_breakdown", {})
        python_files = bug_results.get("total_python_files", 0)
        javascript_files = bug_results.get("total_javascript_files", 0)
        answer = (
            f"The bug analyzer detected {count} finding(s) across "
            f"{python_files} Python file(s) and "
            f"{javascript_files} JavaScript/TypeScript file(s)."
        )
        if breakdown:
            answer += " Severity breakdown: " + ", ".join(f"{level}: {number}" for level, number in breakdown.items()) + "."
        sources = ["backend/bug_analyzer.py"] if (root / "backend/bug_analyzer.py").exists() else ["bug_analyzer.py"]

    elif any(term in q for term in ("quality check", "quality findings", "quality issues", "missing license", "contributing guide")):
        findings = quality_results.get("findings", [])
        count = quality_results.get("findings_count", len(findings))
        answer = f"The repository quality checks found {count} finding(s)."
        if findings:
            answer += "\n" + "\n".join(f"- {item.get('title', item.get('message', item.get('check', str(item))))}" for item in findings[:10])
        sources = ["backend/repository_quality_analyzer.py"] if (root / "backend/repository_quality_analyzer.py").exists() else ["repository_quality_analyzer.py"]

    elif any(term in q for term in ("which file", "what file", "which module", "what module", "responsible for", "which python files")) and any(term in q for term in ("code quality", "quality analysis", "detecting bugs", "bug detection", "analyz", "authentication", "login", "depend")):
        if "depend" in q:
            wanted = ("dependency_analyzer.py",)
        elif any(term in q for term in ("authentication", "login")):
            wanted = ("main.py",)
        else:
            wanted = ("repository_quality_analyzer.py", "bug_analyzer.py", "repository_qa.py")
        matches = [f for f in root.rglob("*.py") if f.name in wanted and not any(part in {".venv", "venv", "node_modules", "__pycache__", ".git"} for part in f.parts)]
        if matches:
            descriptions = {
                "repository_quality_analyzer.py": "checks repository-level quality/documentation conventions",
                "bug_analyzer.py": "scans Python code for code-level findings and calculates the health score",
                "repository_qa.py": "classifies questions and formats answers from analysis results",
                "dependency_analyzer.py": "reads dependency manifests and extracts package information",
                "main.py": "defines the FastAPI endpoints, including authentication routes",
            }
            answer = "Relevant files:\n" + "\n".join(f"- {f.relative_to(root).as_posix()}: {descriptions.get(f.name, 'application module')}" for f in matches)
            sources = [f.relative_to(root).as_posix() for f in matches]
        else:
            answer = "I couldn't find a matching analyzer file in this repository."

    elif any(term in q for term in ("project structure", "repository structure", "directory structure", "folder structure", "show folders", "list folders", "folders and files")):
        if structure:
            lines = ["Repository structure:"]
            for folder, files in structure.items():
                lines.append(f"\n{folder}/")
                for name in files[:12]:
                    lines.append(f"  - {name}")
                    sources.append(name)
            answer = "\n".join(lines)
        else:
            answer = "No repository structure information is available."

    elif any(term in q for term in ("technology", "technologies", "technology stack", "tech stack", "techstack", "framework", "programming language", "which language", "what language", "what stack", "which stack", "what does this project use")):
        detected = [f"{category.replace('_', ' ').title()}: {', '.join(map(str, items))}" for category, items in technologies.items() if items]
        answer = "The detected technology stack is:\n" + "\n".join(detected) if detected else "No supported technologies were detected."
        sources = [item.get("file", "") for item in important_files if item.get("file")]

    elif any(term in q for term in ("depend", "libraries", "packages", "requirements")):
        sections = []
        for label, key in (("Python dependencies", "python"), ("JavaScript dependencies", "javascript")):
            items = dependencies.get(key, [])
            if items:
                sections.append(label + ":")
                for item in items:
                    sections.append(f"- {item.get('name', 'Unknown')}: {item.get('version_specifier', 'Version unspecified')}")
                    if item.get("source"):
                        sources.append(item["source"])
        answer = "Repository dependencies:\n" + "\n".join(sections) if sections else "No supported dependencies were detected."

    elif any(term in q.split() for term in ("imports", "import")) or any(term in q for term in ("relationship", "modules connect", "connected", "application modules")):
        items = relationships.get("relationships", [])
        if "test" not in q:
            items = [item for item in items if not Path(item.get("source_file", "")).name.startswith("test_")]
        if items:
            answer = "Detected code relationships:\n" + "\n".join(f"- {item.get('source_file', '?')} imports {item.get('target_file', '?')}" for item in items[:10])
            for item in items[:10]:
                sources.extend([item.get("source_file", ""), item.get("target_file", "")])
        else:
            answer = "No internal Python import relationships were detected."

    elif any(term in q for term in ("important file", "entry point", "main file", "where is", "authentication", "login", "which files are important")):
        terms = [term for term in ("main.py", "app.py", "app.jsx", "main.jsx", "main.tsx", "index.html", "package.json", "requirements.txt", "repository_qa.py", "bug_analyzer.py", "repository_quality_analyzer.py") if term in q]
        matches = [item for item in important_files if any(term in item.get("file", "").lower() for term in terms)] if terms else important_files
        matches = [item for item in matches if not item.get("file", "").endswith(".gitignore")]
        if matches:
            answer = "Relevant files:\n" + "\n".join(f"- {item['file']}: {item.get('purpose', 'Purpose not documented.') }" for item in matches[:8])
            sources = [item["file"] for item in matches[:8]]
        else:
            answer = "I couldn't identify a matching important file from the available repository analysis."

    elif any(term in q for term in (
        "frontend and backend", "front end and back end", "frontend", "front end",
        "backend", "back end", "work together", "how they work together",
        "application components", "architecture", "responsible for", "what this repository does",
        "what does this repository do", "what does this repo do", "explain this repository",
        "explain this repo", "purpose of this repository", "purpose of this repo",
    )):
        # Give broad architecture questions a useful answer instead of rejecting them
        # just because they do not match one of the narrower analyzer topics.
        detected = [
            f"- {category.replace('_', ' ').title()}: {', '.join(map(str, items))}"
            for category, items in technologies.items() if items
        ]
        key_files = [
            item for item in important_files
            if any(name in item.get("file", "").lower() for name in (
                "main.py", "app.jsx", "main.jsx", "main.tsx", "package.json",
                "repository_qa.py", "repository_summary.py", "bug_analyzer.py",
            ))
        ]
        parts = [f"Repository: {summary.get('repository_name', root.name)}"]
        parts.append(
            "This repository contains application code and repository-analysis tooling. "
            "The backend's Python/FastAPI entry point handles API routes and server-side work; "
            "the React/Vite frontend provides the user interface. The frontend calls backend "
            "API endpoints to request repository analysis and display results."
        )
        if detected:
            parts.append("Detected technologies:\n" + "\n".join(detected))
        if key_files:
            parts.append("Relevant files identified by repository analysis:\n" + "\n".join(
                f"- {item.get('file')}: {item.get('purpose', 'Purpose not documented.')}"
                for item in key_files[:8]
            ))
            sources.extend(item.get("file", "") for item in key_files[:8])
        answer = "\n\n".join(parts)
        sources.extend(item.get("file", "") for item in important_files[:5] if item.get("file"))

    elif any(term in q for term in ("overview", "about this project", "what does this project do", "summarize", "summary")):
        answer = f"Repository: {summary.get('repository_name', root.name)}\nTotal files: {summary.get('total_files', 'unknown')}\nDetected technologies:\n"
        detected = [f"- {category.replace('_', ' ').title()}: {', '.join(map(str, items))}" for category, items in technologies.items() if items]
        answer += "\n".join(detected) if detected else "- No supported technologies detected."
        sources = [item.get("file", "") for item in important_files[:5] if item.get("file")]

    else:
        answer = "I couldn't confidently classify that question. Try asking about bugs/findings, code health score, quality checks, technology stack, dependencies, important files, project structure, code relationships, or the project overview."

    return {"question": question, "answer": answer, "sources": sorted(set(s for s in sources if s))}
