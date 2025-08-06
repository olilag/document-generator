import re
from datetime import datetime
from os import environ
from pathlib import Path

import niquests
from githubkit import GitHub
from githubkit.versions.latest.models import Issue, IssuePropPullRequest

TEST_PREFIX = "testovanie"
DATE_FMT = "%d-%m-%Y-%H:%M:%S"
LABEL_FILTER = "Na testovanie"
INPUT_DIR = "input"


def get_issues(now: datetime, owner: str, repo: str) -> Path:
    t = Path(f"{INPUT_DIR}/{TEST_PREFIX}-{now.strftime(DATE_FMT)}")
    t.mkdir(parents=True)

    g = GitHub(environ["GH_TOKEN"])
    resp = g.rest.issues.list_for_repo(owner, repo, labels=LABEL_FILTER)
    issues: list[Issue] = resp.parsed_data
    for issue in issues:
        _process_issue(issue, t)
    return t


def _process_issue(issue: Issue, parent_dir: Path) -> None:
    # github may lists pull requests as issues
    if isinstance(issue.pull_request, IssuePropPullRequest):
        return

    issue_dir = parent_dir / str(issue.id)
    issue_dir.mkdir()

    with Path.open(issue_dir / "problem.md", "w", encoding="utf-8") as p_file:
        if isinstance(issue.body, str):
            processed = _download_images(issue.body, issue_dir)
            p_file.write(processed)

    with Path.open(issue_dir / "meta.yaml", "w", encoding="utf-8") as m_file:
        m_file.write(f"title: {issue.title}\n")


url_regexp = re.compile(r"https?://[^\")]+")


def _download_images(issue_body: str, issue_dir: Path) -> str:
    urls = url_regexp.findall(issue_body)
    cookies = {"user_session": environ["GH_SESSION"]}

    for url in urls:
        response = niquests.get(url, cookies=cookies)
        if (
            response.status_code == niquests.codes["ok"]
            and response.content is not None
        ):
            file_name = url.split("/")[-1]
            with Path.open(issue_dir / file_name, "wb") as file:
                file.write(response.content)
            issue_body = issue_body.replace(url, file_name, 1)
    return issue_body
