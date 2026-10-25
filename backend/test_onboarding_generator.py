from pathlib import Path

from backend.onboarding_generator import generate_onboarding_document


# Locate the main project directory.
project_root = Path(__file__).resolve().parents[1]

# Generate the onboarding document.
result = generate_onboarding_document(project_root)

print("=" * 45)
print("REPOGUIDE ONBOARDING GENERATOR")
print("=" * 45)

print(f"\nRepository: {result['repository_name']}")
print(f"Output: {result['output_path']}")
print(f"Characters written: {result['characters_written']}")

print("\nREPOGUIDE ONBOARDING DOCUMENT GENERATED SUCCESSFULLY!")