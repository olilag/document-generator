from argparse import ArgumentParser, Namespace

from dotenv import load_dotenv

import pdf_gen
import template_gen

parser = ArgumentParser()
subparsers = parser.add_subparsers()

pdf = subparsers.add_parser("pdf")
pdf.set_defaults(func=pdf_gen.main)

template = subparsers.add_parser("template")
template.add_argument("issue_number", type=int)
template.add_argument("round_number", type=int)
template.add_argument("problem_number", type=int)
template.set_defaults(func=template_gen.main)


def main(args: Namespace) -> None:
    load_dotenv()
    args.func(args)


if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
