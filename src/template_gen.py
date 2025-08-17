from argparse import Namespace
from os import environ
from pathlib import Path

import uvloop

from gh_api import get_issue


def main(args: Namespace) -> None:
    uvloop.run(_main(args.issue_number, args.round_number, args.problem_number))


async def _main(issue_number: int, round_number: int, problem_number: int) -> None:
    owner = environ["REPO_OWNER"]
    repo = environ["REPO_NAME"]
    # TODO: maybe different location
    download_to = Path(f".commit/{round_number}/{problem_number}")
    download_to.mkdir(parents=True, exist_ok=True)

    await get_issue(owner, repo, issue_number, download_to)
