from pathlib import Path

from backend.repository_analyzer import IGNORED_DIRECTORIES

def detect_technology_stack(repository_path):
    """Detect technologies using repository files and configuration."""

    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Expected a directory: {root}"
        )

    detected = {
        "languages": set(),
        "frontend": set(),
        "backend": set(),
        "database": set(),
        "package_managers": set(),
    }

    # Detect technologies from filenames and project structure.
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(root)

        # Ignore generated and environment directories.
        if any(
            part in {
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            }
            for part in relative_path.parts
        ):
            continue

        name = path.name.lower()
        suffix = path.suffix.lower()

        # Programming languages
        if suffix == ".py":
            detected["languages"].add("Python")

        elif suffix in {".js", ".jsx", ".mjs", ".cjs"}:
            detected["languages"].add("JavaScript")

        elif suffix in {".ts", ".tsx"}:
            detected["languages"].add("TypeScript")

        elif suffix == ".java":
            detected["languages"].add("Java")

        elif suffix in {".cpp", ".cc", ".cxx"}:
            detected["languages"].add("C++")

        elif suffix == ".c":
            detected["languages"].add("C")

        # Frontend frameworks and tools
        if name == "vite.config.js" or name == "vite.config.ts":
            detected["frontend"].add("Vite")

        if name in {"package.json", "package-lock.json"}:
            detected["package_managers"].add("npm")

        if name == "package.json":
            try:
                import json

                with path.open("r", encoding="utf-8") as file:
                    package_data = json.load(file)

                dependencies = {}

                dependencies.update(
                    package_data.get("dependencies", {})
                )
                dependencies.update(
                    package_data.get("devDependencies", {})
                )

                if "react" in dependencies:
                    detected["frontend"].add("React")

                if "vite" in dependencies:
                    detected["frontend"].add("Vite")

            except (json.JSONDecodeError, OSError):
                pass

        # Backend frameworks
        if name == "requirements.txt":
            try:
                content = path.read_text(
                    encoding="utf-8"
                ).lower()

                if "fastapi" in content:
                    detected["backend"].add("FastAPI")

                if "flask" in content:
                    detected["backend"].add("Flask")

                if "django" in content:
                    detected["backend"].add("Django")

                if "pymongo" in content or "motor" in content:
                    detected["database"].add("MongoDB")

            except OSError:
                pass

        # Database indicators
        if name in {".env", ".env.example"}:
            try:
                content = path.read_text(
                    encoding="utf-8"
                ).lower()

                if "mongodb://" in content or "mongodb+srv://" in content:
                    detected["database"].add("MongoDB")

            except OSError:
                pass

    # Convert sets into sorted lists for readable output.
    return {
        category: sorted(technologies)
        for category, technologies in detected.items()
    }