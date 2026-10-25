from pathlib import Path
from backend.repository_summary import generate_repository_summary

project_root = Path(__file__).resolve().parents[1]

summary = generate_repository_summary(project_root)

print("=" * 50)
print("REPOGUIDE REPOSITORY SUMMARY")
print("=" * 50)

print(f"\nRepository: {summary['repository_name']}")
print(f"Total files: {summary['total_files']}")

print("\nTECHNOLOGY STACK")
print("-" * 30)

for category, technologies in summary["technology_stack"].items():
    label = category.replace("_", " ").title()
    print(f"{label}: {', '.join(technologies) or 'Not detected'}")

print("\nIMPORTANT FILES")
print("-" * 30)

for item in summary["important_files"]:
    print(f"\n{item['file']}")
    print(f"  Purpose: {item['purpose']}")

print("\n" + "=" * 50)
print("\nPROJECT STRUCTURE")
print("=" * 40)

for folder, files in summary["project_structure"].items():
    print(f"\n{folder}/")

    for file in files:
        print(f"  - {file}")
print("SUMMARY GENERATION COMPLETE")
print("=" * 50)