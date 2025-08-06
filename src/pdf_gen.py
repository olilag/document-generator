import subprocess
from pathlib import Path
from typing import TypedDict

import yaml


class Meta(TypedDict):
    volume: int
    year: str
    round: int | None
    sources: list[str]


OUTPUT_DIR = "output"


def generate_pdf(issue_dir: Path) -> None:
    directories = [
        str(d.relative_to(issue_dir.parent)) for d in issue_dir.iterdir() if d.is_dir()
    ]
    meta = Meta(volume=1, year="2025/2026", round=None, sources=directories)
    with Path.open(issue_dir / "meta.yaml", "w", encoding="utf-8") as meta_file:
        yaml.safe_dump(meta, meta_file)

    _run_typst(issue_dir, Path(OUTPUT_DIR) / issue_dir.name)


def _run_typst(issue_dir: Path, output_dir: Path) -> None:
    cwd = Path.cwd()
    output_dir.mkdir(parents=True)
    typst_cmd = [
        "typst",
        "compile",
        "typst-templates/main.typ",
        "--root",
        str(cwd),
        "--input",
        f"root={issue_dir}",
        f"{output_dir}/testovanie.pdf",
    ]
    subprocess.run(typst_cmd, check=False)
