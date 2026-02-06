import argparse
import sys

from agent.config import load_config
from agent.agent import DebugAgent


def main():
    parser = argparse.ArgumentParser(
        description="AI Debugging Agent - Investigates Cloud Function bugs and opens fix PRs"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=15,
        help="Maximum number of LLM iterations (default: 15)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (show tool arguments and results)",
    )

    args = parser.parse_args()

    # Load and validate config
    config = load_config()

    # Run the agent
    agent = DebugAgent(
        config=config,
        max_iterations=args.max_iterations,
        verbose=args.verbose,
    )

    try:
        agent.run()
    except KeyboardInterrupt:
        print("\n\nAgent interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nAgent failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
