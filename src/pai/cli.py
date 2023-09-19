import argparse

from pai.repl import REPL
from pai.version import VERSION


def parse_args():
    parser = argparse.ArgumentParser(description="pai")

    group = parser.add_mutually_exclusive_group()

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
        "--version",
        help="Print the version and exit.",
        action="version",
        version=VERSION,
    )

    parser.add_argument(
        "prompt", help="The initial prompt for the LLM agent", nargs="?", default=""
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.llama_cpp:
        from pai.llms.llama import LlamaCpp

        llm = LlamaCpp(args.llama_cpp)
    elif args.fake_llm:
        from pai.llms.fake import FakeLLM

        llm = FakeLLM()
    else:
        from pai.llms.chat_gpt import ChatGPT

        llm = ChatGPT(args.openai)

    REPL(llm, args.prompt)


if __name__ == "__main__":
    main()
