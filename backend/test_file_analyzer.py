from pathlib import Path
from backend.file_analyzer import analyze_important_files

project_root = Path(__file__).resolve().parents[1]

import file_analyzer
print("Analyzer loaded from:", file_analyzer.__file__)
result = analyze_important_files(project_root)

print("IMPORTANT FILES")
print("=" * 40)

for item in result:
    print(f"\nFile: {item['file']}")
    print(f"Purpose: {item['purpose']}")

print(f"\nTotal important files found: {len(result)}")