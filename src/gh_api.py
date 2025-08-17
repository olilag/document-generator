import asyncio
import re
from datetime import datetime
from os import environ
from pathlib import Path
from typing import Optional

import niquests
from aiofile import async_open
from githubkit import GitHub
from githubkit.exception import GitHubException
from githubkit.versions.latest.models import Issue, IssuePropPullRequest
from niquests import AsyncSession, RequestException

TEST_PREFIX = "testovanie"
DATE_FMT = "%d-%m-%Y-%H:%M:%S"
LABEL_FILTER = "Na testovanie"
INPUT_DIR = "input"


async def get_issue(
    owner: str, repo: str, issue_number: int, download_to: Path
) -> None:
    g = GitHub(environ["GH_TOKEN"])
    try:
        resp = await g.rest.issues.async_get(owner, repo, issue_number)
    except GitHubException as ex:
        print(f"Error while fetching an issue from GitHub occurred: {ex}")
        raise

    issue = resp.parsed_data

    await _process_issue(issue, download_to)


async def get_issues(owner: str, repo: str) -> Path:
    now = datetime.now()
    t = Path(f"{INPUT_DIR}/{TEST_PREFIX}-{now.strftime(DATE_FMT)}")
    t.mkdir(parents=True)

    g = GitHub(environ["GH_TOKEN"])
    try:
        resp = await g.rest.issues.async_list_for_repo(
            owner, repo, state="open", labels=LABEL_FILTER
        )
    except GitHubException as ex:
        print(f"Error while fetching issues from GitHub occurred: {ex}")
        raise

    issues: list[Issue] = resp.parsed_data
    tasks: list[asyncio.Task[None]] = []
    async with asyncio.TaskGroup() as tg:
        for issue in issues:
            tasks.append(tg.create_task(_process_issue(issue, t)))

    try:
        for task in tasks:
            # for exception propagation
            task.result()
    except ExceptionGroup as ex:
        print(f"Error while processing issues occurred: {ex}")
        raise

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
            processed = await _download_images(issue.title, issue.body, issue_dir)
        await p_file.write(processed)

    async with async_open(issue_dir / "meta.yaml", "w", encoding="utf-8") as m_file:
        await m_file.write(f"title: {issue.title}\n")
        # TODO: get user from issue
        # TODO: get correct answer from issue body


url_regexp = re.compile(r"https?://[^\")]+")


async def _download_images(issue_title: str, issue_body: str, issue_dir: Path) -> str:
    urls = url_regexp.findall(issue_body)
    cookies = {"user_session": environ["GH_SESSION"]}

    url_count = len(urls)
    if url_count == 0:
        # early return, no images need to be downloaded
        return issue_body

    img_str = f"{url_count} image{'' if url_count == 1 else 's'}"
    print(f"Downloading {img_str} for issue: {issue_title}")

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


CONTENT_TYPE_TO_EXTENSION = {
    "image/svg+xml": "svg",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}


async def _download_image(
    s: AsyncSession, issue_dir: Path, url: str, cookies: dict[str, str]
) -> Optional[tuple[str, str]]:
    response = await s.get(url, cookies=cookies)
    try:
        if (
            response.status_code == niquests.codes["ok"]
            and response.content is not None
        ):
            ct = str(response.headers["Content-Type"])
            ext = CONTENT_TYPE_TO_EXTENSION[ct]
            file_name = f"{url.split('/')[-1]}.{ext}"
            async with async_open(issue_dir / file_name, "wb") as file:
                await file.write(response.content)
            return (url, file_name)
    except RequestException as ex:
        print(f"Error while fetching image from {url} occurred: {ex}")
    except (OSError, RuntimeError) as ex:
        print(f"Error while saving image from {url} occurred: {ex}")
    return None
