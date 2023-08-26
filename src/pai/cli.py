import argparse

from pai.console import Console
from pai.llms.chat_gpt import ChatGPT
from pai.llms.fake import FakeLLM
from pai.llms.llama import LlamaCpp
from pai.repl import REPL


def parse_args():
    parser = argparse.ArgumentParser(description="AI REPL")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--chat-gpt",
        help="Use ChatGPT as the llm with the given model. Requires OPENAI_API_KEY in the environment.",
        choices=["gpt-3.5-turbo", "gpt-4"],
        default=None,
    )

    group.add_argument(
        "--llama-cpp",
        help="Use LlamaCpp as the llm with the given model location.",
        metavar="PATH_TO_MODEL",
        type=str,
        default=None,
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

    return parser.parse_args()


def main():
    args = parse_args()

    if args.chat_gpt:
        llm = ChatGPT(args.chat_gpt)
    elif args.llama_cpp:
        llm = LlamaCpp(args.llama_cpp)
    elif args.fake_llm:
        llm = FakeLLM()
    else:
        raise ValueError(f"Must specify an LLM")

    console = Console(llm, llm_context_nodes=args.ctx_history_count)
    repl = REPL(console)
    repl.go()


if __name__ == "__main__":
    main()
