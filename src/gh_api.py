import asyncio
import re
from datetime import datetime
from os import environ
from pathlib import Path
from typing import Optional

import niquests
from aiofile import async_open
from githubkit import GitHub
from githubkit.versions.latest.models import Issue, IssuePropPullRequest
from niquests import AsyncSession

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

    async with async_open(issue_dir / "problem.md", "w", encoding="utf-8") as p_file:
        processed = "missing issue body"
        if isinstance(issue.body, str):
            processed = await _download_images(issue.body, issue_dir)
        await p_file.write(processed)

    async with async_open(issue_dir / "meta.yaml", "w", encoding="utf-8") as m_file:
        await m_file.write(f"title: {issue.title}\n")


url_regexp = re.compile(r"https?://[^\")]+")


async def _download_images(issue_body: str, issue_dir: Path) -> str:
    urls = url_regexp.findall(issue_body)
    cookies = {"user_session": environ["GH_SESSION"]}

    tasks: list[asyncio.Task[Optional[tuple[str, str]]]] = []
    async with AsyncSession() as s:
        async with asyncio.TaskGroup() as tg:
            for url in urls:
                tasks.append(
                    tg.create_task(_download_image(s, issue_dir, url, cookies))
                )

    for task in tasks:
        r = task.result()
        if r is None:
            continue
        issue_body = issue_body.replace(r[0], r[1])

    return issue_body


async def _download_image(
    s: AsyncSession, issue_dir: Path, url: str, cookies: dict[str, str]
) -> Optional[tuple[str, str]]:
    response = await s.get(url, cookies=cookies)
    if response.status_code == niquests.codes["ok"] and response.content is not None:
        file_name = url.split("/")[-1]
        async with async_open(issue_dir / file_name, "wb") as file:
            await file.write(response.content)
        return (url, file_name)
    return None
