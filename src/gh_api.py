import asyncio
import re
from datetime import datetime
from os import environ
from pathlib import Path
from typing import Optional

import niquests
from githubkit import GitHub
from githubkit.versions.latest.models import Issue, IssuePropPullRequest

TEST_PREFIX = "testovanie"
DATE_FMT = "%d-%m-%Y-%H:%M:%S"
LABEL_FILTER = "Na testovanie"
INPUT_DIR = "input"


async def get_issues(now: datetime, owner: str, repo: str) -> Path:
    t = Path(f"{INPUT_DIR}/{TEST_PREFIX}-{now.strftime(DATE_FMT)}")
    t.mkdir(parents=True)

    g = GitHub(environ["GH_TOKEN"])
    resp = await g.rest.issues.async_list_for_repo(
        owner, repo, state="open", labels=LABEL_FILTER
    )
    issues: list[Issue] = resp.parsed_data
    # tasks: list[Task] = []
    async with asyncio.TaskGroup() as tg:
        for issue in issues:
            tg.create_task(_process_issue(issue, t))
    return t


async def _process_issue(issue: Issue, parent_dir: Path) -> None:
    # github considers pull requests as issues
    if isinstance(issue.pull_request, IssuePropPullRequest):
        return

    issue_dir = parent_dir / str(issue.id)
    issue_dir.mkdir()

    print(f"Saving issue: {issue.title}")

    with issue_dir.joinpath("problem.md").open("w", encoding="utf-8") as p_file:
        if isinstance(issue.body, str):
            processed = await _download_images(issue.body, issue_dir)
            p_file.write(processed)

    with issue_dir.joinpath("meta.yaml").open("w", encoding="utf-8") as m_file:
        m_file.write(f"title: {issue.title}\n")


url_regexp = re.compile(r"https?://[^\")]+")


async def _download_images(issue_body: str, issue_dir: Path) -> str:
    urls = url_regexp.findall(issue_body)
    cookies = {"user_session": environ["GH_SESSION"]}

    tasks: list[asyncio.Task[Optional[tuple[str, str]]]] = []
    async with asyncio.TaskGroup() as tg:
        for url in urls:
            tasks.append(tg.create_task(_download_image(issue_dir, url, cookies)))

    for task in tasks:
        r = task.result()
        if r is None:
            continue
        issue_body = issue_body.replace(r[0], r[1])

    return issue_body


async def _download_image(
    issue_dir: Path, url: str, cookies: dict[str, str]
) -> Optional[tuple[str, str]]:
    response = await niquests.aget(url, cookies=cookies)
    if response.status_code == niquests.codes["ok"] and response.content is not None:
        file_name = url.split("/")[-1]
        with issue_dir.joinpath(file_name).open("wb") as file:
            file.write(response.content)
        return (url, file_name)
    return None
