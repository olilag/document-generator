from os import environ

from dotenv import load_dotenv

from gh_api import get_issues
from pdf_gen import generate_pdf


def main() -> None:
    load_dotenv()
    d = get_issues(f"{environ['REPO_OWNER']}/{environ['REPO_NAME']}")
    generate_pdf(d)


if __name__ == "__main__":
    main()
