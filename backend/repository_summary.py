from pathlib import Path

from backend.repository_analyzer import scan_repository
from backend.technology_detector import detect_technology_stack
from backend.file_analyzer import analyze_important_files
from backend.dependency_analyzer import analyze_dependencies
from backend.code_relationship_analyzer import analyze_code_relationships



def generate_repository_summary(repository_path):
    """Generate a structured summary of a software repository."""

    root = Path(repository_path).resolve()

    # Collect information from our existing components.
    inventory = scan_repository(root)
    technologies = detect_technology_stack(root)
    important_files = analyze_important_files(root)
    dependencies = analyze_dependencies(root)
    code_relationships = analyze_code_relationships(root)
    

        # Build a simple overview of the repository structure. Store paths relative
    # to each displayed top-level folder so output does not repeat "backend/".
    structure = {}
    for file in inventory["files"]:
        path = Path(file)
        parts = path.parts
        if len(parts) == 1:
            structure.setdefault("Root", []).append(path.name)
        else:
            folder = parts[0]
            display_name = Path(*parts[1:]).as_posix()
            structure.setdefault(folder, []).append(display_name)

    summary = {
    "repository_name": root.name,
    "repository_path": str(root),
    "total_files": inventory["total_files"],
    "technology_stack": technologies,
    "dependencies": dependencies,
    "important_files": important_files,
    "project_structure": structure,
    "code_relationships": code_relationships,
}

    return summary