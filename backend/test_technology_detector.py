from pathlib import Path
from backend.technology_detector import detect_technology_stack

project_root = Path(__file__).resolve().parents[1]

result = detect_technology_stack(project_root)

print("TECHNOLOGY STACK DETECTED")
print("-" * 35)

for category, technologies in result.items():
    print(f"{category.replace('_', ' ').title()}: ", end="")
    print(", ".join(technologies) if technologies else "Not detected")