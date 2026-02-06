import os
import sys

from dotenv import load_dotenv


def load_config() -> dict:
    """Load and validate configuration from .env file."""
    load_dotenv()

    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key for the LLM",
        "GCP_PROJECT_ID": "GCP project ID",
        "GCP_FUNCTION_NAME": "Name of the deployed Cloud Function",
        "GCP_SA_KEY_BASE64": "Base64-encoded GCP service account JSON key",
        "GITHUB_TOKEN": "GitHub personal access token with repo scope",
        "GITHUB_REPO": "GitHub repo in owner/repo format",
    }

    config = {}
    missing = []

    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            missing.append(f"  - {var}: {description}")
        else:
            config[var] = value

    if missing:
        print("ERROR: Missing required environment variables:\n")
        print("\n".join(missing))
        print("\nPlease set them in the .env file. See .env.example for reference.")
        sys.exit(1)

    return config
