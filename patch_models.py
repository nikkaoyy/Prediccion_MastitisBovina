import sys
from pathlib import Path
import re

def patch_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Insert sys.path...
    if "sys.path.insert(0, str(Path(__file__).resolve().parents[2]))" not in content:
        content = re.sub(
            r"(from __future__ import annotations\n)",
            r"\1\nimport sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parents[2]))\n",
            content
        )

    # 2. Add make_scorer
    if "make_scorer" not in content:
        content = re.sub(
            r"(from sklearn\.metrics import \(\n(?:.*?)\n\))",
            r"\1\nfrom sklearn.metrics import make_scorer",
            content,
            flags=re.DOTALL
        )
        if "make_scorer" not in content:
            # Maybe it's not a multiline import
            content = re.sub(r"(import pandas as pd\n)", r"\1from sklearn.metrics import make_scorer\n", content)


    # 3. Modify scoring
    content = content.replace('scoring="f1",', 'scoring=make_scorer(f1_score, zero_division=0),')

    # 4. Reduce grids
    if "DecisionTreeTraining" in file_path:
        content = re.sub(
            r'DEFAULT_PARAM_GRID: dict\[str, list\[Any\]\] = \{.*?\}',
            'DEFAULT_PARAM_GRID: dict[str, list[Any]] = {\n        "classifier__criterion": ["gini"],\n        "classifier__max_depth": [5, None],\n        "classifier__min_samples_split": [2],\n        "classifier__min_samples_leaf": [1],\n        "classifier__class_weight": ["balanced"],\n    }',
            content,
            flags=re.DOTALL
        )
    elif "LogisticalRegresion" in file_path:
        content = re.sub(
            r'DEFAULT_PARAM_GRID: dict\[str, list\[Any\]\] = \{.*?\}',
            'DEFAULT_PARAM_GRID: dict[str, list[Any]] = {\n        "classifier__C": [1.0],\n        "classifier__penalty": ["l2"],\n        "classifier__class_weight": ["balanced"],\n    }',
            content,
            flags=re.DOTALL
        )
    elif "RandomForest" in file_path:
        content = re.sub(
            r'DEFAULT_PARAM_GRID: dict\[str, list\[Any\]\] = \{.*?\}',
            'DEFAULT_PARAM_GRID: dict[str, list[Any]] = {\n        "classifier__n_estimators": [50],\n        "classifier__max_depth": [5, None],\n        "classifier__min_samples_split": [2],\n        "classifier__class_weight": ["balanced"],\n    }',
            content,
            flags=re.DOTALL
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def patch_main():
    file_path = "main.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # main.py changes
    content = content.replace(
        'artifacts_dir: str | Path = "src/data/artifacts",',
        'artifacts_dir: str | Path = PROJECT_ROOT / "src/data/artifacts",'
    )
    content = content.replace(
        'reports_dir: str | Path = "demo_reports",',
        'reports_dir: str | Path = PROJECT_ROOT / "demo_reports",'
    )
    content = content.replace(
        'default=Path("src/data/artifacts"),',
        'default=PROJECT_ROOT / "src/data/artifacts",'
    )
    content = content.replace(
        'default=Path("demo_reports"),',
        'default=PROJECT_ROOT / "demo_reports",'
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def patch_generate():
    file_path = "generateDecisionTree.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace(
        'DEFAULT_ARTIFACTS_DIR = Path("src/data/artifacts")',
        'DEFAULT_ARTIFACTS_DIR = PROJECT_ROOT / "src/data/artifacts"'
    )
    content = content.replace(
        'default=Path("demo_reports"),',
        'default=PROJECT_ROOT / "demo_reports",'
    )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    patch_file("src/models/DecisionTreeTraining.py")
    patch_file("src/models/LogisticalRegresion.py")
    patch_file("src/models/RandomForest.py")
    patch_main()
    patch_generate()
    print("Done")
