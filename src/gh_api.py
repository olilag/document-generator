import asyncio
import base64
import re
from html.parser import HTMLParser
from os import environ
from pathlib import Path
from typing import Optional, cast

import niquests
from aiofile import async_open
from githubkit import GitHub
from githubkit.exception import GitHubException
from githubkit.versions.latest.models import Issue, IssuePropPullRequest
from githubkit.versions.latest.types import (
    ReposOwnerRepoGitTreesPostBodyPropTreeItemsType,
)
from niquests import AsyncSession, RequestException

LABEL_FILTER = "Na testovanie"
GH_API = GitHub(environ["GH_TOKEN"])


async def create_pull_request(  # noqa: PLR0913
    owner: str,
    repo: str,
    from_branch: str,
    to_branch: str,
    title: str,
    content: str,
    draft: bool = False,
) -> None:
    await GH_API.rest.pulls.async_create(
        owner,
        repo,
        head=from_branch,
        base=to_branch,
        title=title,
        body=content,
        maintainer_can_modify=True,
        draft=draft,
    )
    # TODO: maybe add some labels and stuff to the PR


async def commit_directory(
    owner: str, repo: str, branch: str, directory: Path, git_path: str
) -> None:
    resp_ref = await GH_API.rest.git.async_get_ref(owner, repo, "heads/master")
    master_ref = resp_ref.parsed_data

    resp_ref = await GH_API.rest.git.async_create_ref(
        owner, repo, ref=f"refs/heads/{branch}", sha=master_ref.object_.sha
    )
    branch_ref = resp_ref.parsed_data

    tree = await _create_git_tree(owner, repo, directory, git_path)
    resp_tree = await GH_API.rest.git.async_create_tree(
        owner,
        repo,
        base_tree=branch_ref.object_.sha,
        tree=tree,
    )
    commit_tree = resp_tree.parsed_data

    resp_commit = await GH_API.rest.git.async_create_commit(
        owner,
        repo,
        message=f"{git_path}: add problem from issue",
        tree=commit_tree.sha,
        parents=[branch_ref.object_.sha],
    )
    commit = resp_commit.parsed_data

    await GH_API.rest.git.async_update_ref(
        owner, repo, f"heads/{branch}", sha=commit.sha
    )


async def _create_git_tree(
    owner: str,
    repo: str,
    directory: Path,
    git_path: str,
) -> list[ReposOwnerRepoGitTreesPostBodyPropTreeItemsType]:
    tasks: list[asyncio.Task[ReposOwnerRepoGitTreesPostBodyPropTreeItemsType]] = []
    async with asyncio.TaskGroup() as tg:
        for file in directory.iterdir():
            tasks.append(
                tg.create_task(_create_git_tree_part(owner, repo, file, git_path))
            )

    result: list[ReposOwnerRepoGitTreesPostBodyPropTreeItemsType] = []
    for task in tasks:
        result.append(task.result())

    return result


async def _create_git_tree_part(
    owner: str, repo: str, file: Path, git_path: str
) -> ReposOwnerRepoGitTreesPostBodyPropTreeItemsType:
    async with async_open(file, "rb") as f:
        content = base64.b64encode(await f.read())

    resp = await GH_API.rest.git.async_create_blob(
        owner, repo, content=content.decode("utf-8"), encoding="base64"
    )
    blob = resp.parsed_data

    return {
        "path": f"{git_path}/{file.name}",
        "sha": blob.sha,
        "mode": "100644",
        "type": "blob",
    }


async def get_issue(
    owner: str, repo: str, issue_number: int, download_to: Path
) -> None:
    try:
        resp = await GH_API.rest.issues.async_get(owner, repo, issue_number)
    except GitHubException as ex:
        print(f"Error while fetching an issue from GitHub occurred: {ex}")
        raise

    issue = resp.parsed_data

    await _process_issue(issue, download_to, False)


async def get_issues(owner: str, repo: str, download_to: Path) -> None:
    try:
        resp = await GH_API.rest.issues.async_list_for_repo(
            owner, repo, state="open", labels=LABEL_FILTER
        )
    except GitHubException as ex:
        print(f"Error while fetching issues from GitHub occurred: {ex}")
        raise

    issues: list[Issue] = resp.parsed_data
    tasks: list[asyncio.Task[None]] = []
    async with asyncio.TaskGroup() as tg:
        for issue in issues:
            tasks.append(tg.create_task(_process_issue(issue, download_to)))

    try:
        for task in tasks:
            # for exception propagation
            task.result()
    except ExceptionGroup as ex:
        print(f"Error while processing issues occurred: {ex}")
        raise


async def _process_issue(
    issue: Issue, parent_dir: Path, create_issue_dir: bool = True
) -> None:
    # github considers pull requests as issues
    if isinstance(issue.pull_request, IssuePropPullRequest):
        return

    if create_issue_dir:
        issue_dir = parent_dir / str(issue.id)
        issue_dir.mkdir()
    else:
        issue_dir = parent_dir

    print(f"Saving issue: {issue.title}")

    async with async_open(issue_dir / "problem.md", "w", encoding="utf-8") as p_file:
        processed = "missing issue body"
        if isinstance(issue.body, str):
            processed = await _download_images(issue.title, issue.body, issue_dir)
        await p_file.write(processed)

    answer = _extract_answer(cast(str, issue.body))
    async with async_open(issue_dir / "meta.yaml", "w", encoding="utf-8") as m_file:
        await m_file.write(f"title: {issue.title}\n")
        if answer is not None:
            await m_file.write(f"answer: {answer}\n")
        # TODO: get user from issue


DETAILS_REGEXP = re.compile(r"<details>(?:.|\n)*?Heslo(?:.|\n)*?</details>")


class DetailsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_details = False
        self._tag_depth = 0
        self.answer: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._in_details:
            self._tag_depth += 1
            return

        if tag == "details":
            self._in_details = True

    def handle_data(self, data: str) -> None:
        if self._tag_depth == 0:
            self.answer = data.strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "details" and self._tag_depth == 0:
            self._in_details = False

        if self._in_details:
            self._tag_depth -= 1


def _extract_answer(issue_body: str) -> Optional[str]:
    match = DETAILS_REGEXP.search(issue_body)
    if match is None:
        return None

    details = match.group(0)
    parser = DetailsParser()
    parser.feed(details)
    return parser.answer


URL_REGEXP = re.compile(r"https?://[^\")]+")


async def _download_images(issue_title: str, issue_body: str, issue_dir: Path) -> str:
    urls = URL_REGEXP.findall(issue_body)
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
