import argparse

from pai.console import Console
from pai.llms.chat_gpt import ChatGPT
from pai.repl import REPL


def parse_args():
    parser = argparse.ArgumentParser(description="AI REPL")
    parser.add_argument(
        "--llm",
        help="Which llm to use",
        choices=["gpt-3.5-turbo", "gpt-4"],
        default="gpt-4",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    llm = ChatGPT(args.llm)
    console = Console(llm)
    repl = REPL(console)
    repl.go()


if __name__ == "__main__":
    main()
