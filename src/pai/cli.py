import argparse

from pai.console import Console
from pai.llms.chat_gpt import ChatGPT
from pai.llms.fake import FakeLLM
from pai.repl import REPL


def parse_args():
    parser = argparse.ArgumentParser(description="AI REPL")
    parser.add_argument(
        "--llm",
        help="Which llm to use",
        choices=["gpt-3.5-turbo", "gpt-4", "fake"],
        default="gpt-4",
    )
    parser.add_argument(
        "--llm-context-history",
        help="How many history nodes to send to the llm as context. Defaults to all of them.",
        type=int,
        default=None,
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.llm == "gpt-3.5-turbo" or args.llm == "gpt-4":
        llm = ChatGPT(args.llm)
    elif args.llm == "fake":
        llm = FakeLLM()
    else:
        raise ValueError(f"Invalid llm: {args.llm}")

    console = Console(llm, llm_context_nodes=args.llm_context_history)
    repl = REPL(console)
    repl.go()


if __name__ == "__main__":
    main()
