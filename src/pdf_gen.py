import subprocess
from argparse import Namespace
from os import environ
from pathlib import Path
from typing import Optional, TypedDict

import uvloop
import yaml

from gh_api import get_issues


def main(args: Namespace) -> None:
    uvloop.run(_main(args.regenerate))


async def _main(directory: Optional[Path]) -> None:
    if directory is None:
        owner = environ["REPO_OWNER"]
        repo = environ["REPO_NAME"]
        print(f"Downloading issues from repo https://github.com/{owner}/{repo} ...")
        directory = await get_issues(owner, repo)
        print("Download complete...")

    if _generate_pdf(directory):
        print("Done")


class Meta(TypedDict):
    volume: int
    year: str
    round: int | None
    sources: list[str]


OUTPUT_DIR = "output"


def _generate_pdf(issue_dir: Path) -> bool:
    directories = [
        str(d.relative_to(issue_dir.parent)) for d in issue_dir.iterdir() if d.is_dir()
    ]
    meta = Meta(volume=1, year="2025/2026", round=None, sources=directories)
    with issue_dir.joinpath("meta.yaml").open("w", encoding="utf-8") as meta_file:
        yaml.safe_dump(meta, meta_file)

    return _run_typst(issue_dir, Path(OUTPUT_DIR) / issue_dir.name)


def _run_typst(issue_dir: Path, output_dir: Path) -> bool:
    cwd = Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
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
    print(f"Generating pdf using: '{' '.join(typst_cmd)}'")
    try:
        subprocess.run(typst_cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as ex:
        print(f"typst failed with error: {ex.stderr}")
        return False
