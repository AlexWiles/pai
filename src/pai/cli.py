import argparse
import toml

from pai.console import Console
from pai.llms.chat_gpt import ChatGPT
from pai.llms.fake import FakeLLM
from pai.llms.llama import LlamaCpp
from pai.repl import REPL
from pai.version import VERSION


def parse_args():
    parser = argparse.ArgumentParser(description="AI REPL")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--llama-cpp",
        help="Use LlamaCpp as the llm with the given model location.",
        metavar="PATH_TO_MODEL",
        type=str,
        default=None,
    )
    group.add_argument(
        "--openai",
        help="Use ChatGPT as the llm with the given model. Requires OPENAI_API_KEY in the environment.",
        choices=["gpt-3.5-turbo", "gpt-4"],
        default="gpt-4",
    )
    group.add_argument(
        "--fake-llm",
        help=argparse.SUPPRESS,
        action="store_true",
    )

    parser.add_argument(
        "--ctx-history-count",
        help="How many history nodes to send to the llm as context. Defaults to all of them.",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--version",
        help="Print the version and exit.",
        action="version",
        version=VERSION,
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.llama_cpp:
        llm = LlamaCpp(args.llama_cpp)
    elif args.fake_llm:
        llm = FakeLLM()
    elif args.openai:
        # openai has a default, so we check last
        llm = ChatGPT(args.openai)
    else:
        raise ValueError(f"Must specify an LLM")

    console = Console(llm, llm_context_nodes=args.ctx_history_count)
    repl = REPL(console)
    repl.go()


if __name__ == "__main__":
    main()
