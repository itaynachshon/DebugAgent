import json

from github import Github, GithubException


def _get_repo(config: dict):
    """Get authenticated PyGithub repo object."""
    g = Github(config["GITHUB_TOKEN"])
    return g.get_repo(config["GITHUB_REPO"])


def list_repo_files(config: dict, path: str = "") -> str:
    """
    List files and directories at a given path in the repository.

    Args:
        config: Application configuration dict.
        path: Path within the repository (empty string for root).

    Returns:
        JSON string listing file names and types.
    """
    repo = _get_repo(config)
    try:
        contents = repo.get_contents(path)
        if not isinstance(contents, list):
            contents = [contents]

        results = []
        for item in contents:
            results.append({
                "name": item.name,
                "path": item.path,
                "type": item.type,  # "file" or "dir"
                "size": item.size,
            })

        return json.dumps(results, indent=2)
    except GithubException as e:
        return json.dumps({"error": str(e)})


def get_file_content(config: dict, path: str, ref: str = "main") -> str:
    """
    Read the content of a file from the repository.

    Args:
        config: Application configuration dict.
        path: Path to the file within the repository.
        ref: Branch or commit reference (default: main).

    Returns:
        The file content as a string.
    """
    repo = _get_repo(config)
    try:
        file_content = repo.get_contents(path, ref=ref)
        return file_content.decoded_content.decode("utf-8")
    except GithubException as e:
        return json.dumps({"error": str(e)})


def create_branch(config: dict, branch_name: str) -> str:
    """
    Create a new branch off main.

    Args:
        config: Application configuration dict.
        branch_name: Name for the new branch.

    Returns:
        JSON string with branch creation result.
    """
    repo = _get_repo(config)
    try:
        main_ref = repo.get_git_ref("heads/main")
        sha = main_ref.object.sha
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sha)
        return json.dumps({"success": True, "branch": branch_name, "base_sha": sha})
    except GithubException as e:
        return json.dumps({"error": str(e)})


def commit_file_change(config: dict, path: str, content: str, message: str, branch: str) -> str:
    """
    Update or create a file on a branch with a commit.

    Args:
        config: Application configuration dict.
        path: Path to the file within the repository.
        content: New file content.
        message: Commit message.
        branch: Branch to commit to.

    Returns:
        JSON string with commit result.
    """
    repo = _get_repo(config)
    try:
        # Try to get existing file to update it
        existing = repo.get_contents(path, ref=branch)
        result = repo.update_file(
            path=path,
            message=message,
            content=content,
            sha=existing.sha,
            branch=branch,
        )
        return json.dumps({
            "success": True,
            "action": "updated",
            "commit_sha": result["commit"].sha,
        })
    except GithubException:
        # File doesn't exist, create it
        try:
            result = repo.create_file(
                path=path,
                message=message,
                content=content,
                branch=branch,
            )
            return json.dumps({
                "success": True,
                "action": "created",
                "commit_sha": result["commit"].sha,
            })
        except GithubException as e:
            return json.dumps({"error": str(e)})


def create_pull_request(config: dict, title: str, body: str, head_branch: str, base_branch: str = "main") -> str:
    """
    Open a pull request.

    Args:
        config: Application configuration dict.
        title: PR title.
        body: PR description/body.
        head_branch: The branch containing the changes.
        base_branch: The branch to merge into (default: main).

    Returns:
        JSON string with PR details including URL.
    """
    repo = _get_repo(config)
    try:
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head_branch,
            base=base_branch,
        )
        return json.dumps({
            "success": True,
            "pr_number": pr.number,
            "pr_url": pr.html_url,
            "title": pr.title,
        })
    except GithubException as e:
        return json.dumps({"error": str(e)})
