from argparse import Namespace
from os import environ
from pathlib import Path

import uvloop

from gh_api import commit_directory, create_pull_request, get_issue


def main(args: Namespace) -> None:
    uvloop.run(_main(args.issue_number, args.round_number, args.problem_number))


INPUT_DIR = "input"
COMMIT_PREFIX = "commit"


async def _main(issue_number: int, round_number: int, problem_number: int) -> None:
    # TODO: add logging and error handling
    owner = environ["REPO_OWNER"]
    repo = environ["REPO_NAME"]
    download_to = (
        Path(INPUT_DIR) / f"{COMMIT_PREFIX}" / str(round_number) / str(problem_number)
    )
    download_to.mkdir(parents=True, exist_ok=True)

    await get_issue(owner, repo, issue_number, download_to)

    branch_name = f"{round_number}/{problem_number}-problem"
    git_path = f"{round_number}/{problem_number}"
    await commit_directory(
        owner,
        repo,
        branch_name,
        download_to,
        git_path,
    )

    pull_title = f"{git_path}: Add problem"
    # TODO: better pull content
    pull_content = f"closes #{issue_number}"
    await create_pull_request(
        owner, repo, branch_name, "master", pull_title, pull_content, draft=True
    )
