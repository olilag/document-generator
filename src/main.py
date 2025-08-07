from datetime import datetime
from os import environ

import uvloop
from dotenv import load_dotenv

from gh_api import get_issues
from pdf_gen import generate_pdf


async def main() -> None:
    load_dotenv()
    now = datetime.now()
    owner = environ["REPO_OWNER"]
    repo = environ["REPO_NAME"]
    print(f"Downloading issues from repo https://github.com/{owner}/{repo} ...")
    d = await get_issues(now, owner, repo)
    print("Download complete...")
    generate_pdf(d)
    print("done")


if __name__ == "__main__":
    uvloop.run(main())
