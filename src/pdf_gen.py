from argparse import Namespace
from datetime import datetime
from os import environ
from pathlib import Path
from typing import Optional, TypedDict

import typst
import uvloop
import yaml

from gh_api import get_issues


def main(args: Namespace) -> None:
    uvloop.run(_main(args.regenerate))


INPUT_DIR = "input"
TEST_PREFIX = "testovanie"
DATE_FMT = "%d-%m-%Y-%H:%M:%S"


async def _main(directory: Optional[Path]) -> None:
    if directory is None:
        owner = environ["REPO_OWNER"]
        repo = environ["REPO_NAME"]
        now = datetime.now()
        directory = Path(INPUT_DIR) / f"{TEST_PREFIX}-{now.strftime(DATE_FMT)}"
        directory.mkdir(parents=True)
        print(f"Downloading issues from repo https://github.com/{owner}/{repo} ...")
        await get_issues(owner, repo, directory)
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
    print("Generating pdf with typst")
    try:
        typst.compile(
            "typst-templates/main.typ",
            output=f"{output_dir}/testovanie.pdf",
            root=str(cwd),
            sys_inputs={"root": str(issue_dir)},
        )
        return True
    except typst.TypstError as ex:
        print(f"Typst failed with message: {ex.message}")
        return False
