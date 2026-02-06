import json
from typing import Callable

from agent.tools import gcp_logging, github

# OpenAI function schemas for all tools
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "query_logs",
            "description": (
                "Query GCP Cloud Logging with a custom filter string. "
                "Use Cloud Logging filter syntax, e.g.: "
                'resource.type="cloud_run_revision" severity>=ERROR'
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_str": {
                        "type": "string",
                        "description": "Cloud Logging filter expression.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of log entries to return (default: 50).",
                    },
                },
                "required": ["filter_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_log_entries",
            "description": (
                "List recent log entries for the deployed Cloud Function. "
                "Returns logs from the last N hours."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the Cloud Function to get logs for.",
                    },
                    "hours_ago": {
                        "type": "integer",
                        "description": "How many hours back to search (default: 24).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of log entries to return (default: 50).",
                    },
                },
                "required": ["function_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_repo_files",
            "description": "List files and directories at a given path in the GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path within the repository (empty string for root).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Read the content of a file from the GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file within the repository.",
                    },
                    "ref": {
                        "type": "string",
                        "description": "Branch or commit reference (default: main).",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_branch",
            "description": "Create a new branch off main in the GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_name": {
                        "type": "string",
                        "description": "Name for the new branch.",
                    },
                },
                "required": ["branch_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "commit_file_change",
            "description": "Update or create a file on a branch with a commit in the GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file within the repository.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The new full file content.",
                    },
                    "message": {
                        "type": "string",
                        "description": "Commit message describing the change.",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch to commit to.",
                    },
                },
                "required": ["path", "content", "message", "branch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pull_request",
            "description": "Open a pull request in the GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "PR title.",
                    },
                    "body": {
                        "type": "string",
                        "description": "PR description/body in markdown.",
                    },
                    "head_branch": {
                        "type": "string",
                        "description": "Branch containing the changes.",
                    },
                    "base_branch": {
                        "type": "string",
                        "description": "Branch to merge into (default: main).",
                    },
                },
                "required": ["title", "body", "head_branch"],
            },
        },
    },
]


def dispatch(tool_name: str, arguments: dict, config: dict) -> str:
    """
    Execute a tool by name with the given arguments.

    Args:
        tool_name: Name of the tool to call.
        arguments: Dictionary of arguments for the tool.
        config: Application configuration dict.

    Returns:
        Tool result as a string.
    """
    handlers: dict[str, Callable] = {
        "query_logs": lambda args: gcp_logging.query_logs(
            config, args["filter_str"], args.get("limit", 50)
        ),
        "list_log_entries": lambda args: gcp_logging.list_log_entries(
            config, args["function_name"], args.get("hours_ago", 24), args.get("limit", 50)
        ),
        "list_repo_files": lambda args: github.list_repo_files(
            config, args.get("path", "")
        ),
        "get_file_content": lambda args: github.get_file_content(
            config, args["path"], args.get("ref", "main")
        ),
        "create_branch": lambda args: github.create_branch(
            config, args["branch_name"]
        ),
        "commit_file_change": lambda args: github.commit_file_change(
            config, args["path"], args["content"], args["message"], args["branch"]
        ),
        "create_pull_request": lambda args: github.create_pull_request(
            config, args["title"], args["body"], args["head_branch"], args.get("base_branch", "main")
        ),
    }

    handler = handlers.get(tool_name)
    if not handler:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        return handler(arguments)
    except Exception as e:
        return json.dumps({"error": f"Tool '{tool_name}' failed: {str(e)}"})
