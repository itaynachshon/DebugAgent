import json

from openai import OpenAI

from agent.prompts import SYSTEM_PROMPT, get_user_prompt
from agent.tools import TOOL_SCHEMAS, dispatch


class DebugAgent:
    """AI debugging agent that investigates bugs and opens fix PRs."""

    def __init__(self, config: dict, max_iterations: int = 15, verbose: bool = False):
        self.config = config
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.client = OpenAI(api_key=config["OPENAI_API_KEY"])
        self.model = "gpt-4o"
        self.messages = []

    def _log(self, message: str) -> None:
        """Print a message if verbose mode is on."""
        if self.verbose:
            print(message)

    def _print_step(self, iteration: int, message: str) -> None:
        """Print agent progress."""
        print(f"\n[Step {iteration}] {message}")

    def run(self) -> str:
        """
        Run the agent loop.

        Returns:
            The agent's final summary message.
        """
        # Initialize conversation
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": get_user_prompt(
                    self.config["GCP_FUNCTION_NAME"],
                    self.config["GCP_PROJECT_ID"],
                ),
            },
        ]

        print("=" * 60)
        print("  AI Debugging Agent Started")
        print("=" * 60)
        print(f"  Target: {self.config['GCP_FUNCTION_NAME']}")
        print(f"  Project: {self.config['GCP_PROJECT_ID']}")
        print(f"  Repo: {self.config['GITHUB_REPO']}")
        print(f"  Max iterations: {self.max_iterations}")
        print("=" * 60)

        for iteration in range(1, self.max_iterations + 1):
            # Call the LLM
            self._log(f"\n--- Iteration {iteration} ---")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_SCHEMAS,
            )

            message = response.choices[0].message

            # If no tool calls, the agent is done
            if not message.tool_calls:
                final_message = message.content or "Agent finished without a summary."
                self.messages.append({"role": "assistant", "content": final_message})
                print("\n" + "=" * 60)
                print("  Agent Completed")
                print("=" * 60)
                print(f"\n{final_message}")
                return final_message

            # Process tool calls
            self.messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                self._print_step(iteration, f"Calling tool: {tool_name}")
                self._log(f"  Arguments: {json.dumps(arguments, indent=2)}")

                # Execute the tool
                result = dispatch(tool_name, arguments, self.config)

                self._log(f"  Result preview: {result[:200]}...")

                # Append tool result to conversation
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        # Max iterations reached
        print("\n" + "=" * 60)
        print("  Agent reached maximum iterations")
        print("=" * 60)
        return "Agent reached maximum iterations without completing the task."
