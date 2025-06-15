import os
from github import Github
from github.GithubException import GithubException

def get_or_create_issue(repo_name: str, label_name: str, issue_title: str) -> int:
    '''
    Finds an open issue with a specific label or creates a new one.

    Args:
        repo_name (str): The owner/repository name (e.g., 'octocat/Hello-World').
        label_name (str): The label to search for or apply to a new issue.
        issue_title (str): The title for the issue if it needs to be created.

    Returns:
        int: The issue number.

    Raises:
        Exception: If there's an error interacting with the GitHub API or if GITHUB_TOKEN is not set.
    '''
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is not set.")

    g = Github(github_token)

    try:
        repo = g.get_repo(repo_name)
    except GithubException as e:
        print(f"Error getting repository '{repo_name}': {e}")
        raise

    try:
        # Check if the label exists, create if not
        try:
            repo.get_label(label_name)
        except GithubException as e:
            if e.status == 404:
                print(f"Label '{label_name}' not found, creating it.")
                repo.create_label(label_name, "4caf50") # Default green color
            else:
                raise

        issues = repo.get_issues(state='open', labels=[label_name])

        found_issues = list(issues) # Convert PaginatedList to list to check length and sort

        if found_issues:
            # Sort by creation date, oldest first
            found_issues.sort(key=lambda i: i.created_at)
            print(f"Found existing issue #{found_issues[0].number} with label '{label_name}'.")
            return found_issues[0].number
        else:
            print(f"No open issue found with label '{label_name}'. Creating a new one.")
            new_issue = repo.create_issue(
                title=issue_title,
                labels=[label_name]
            )
            print(f"Created new issue #{new_issue.number} with title '{issue_title}' and label '{label_name}'.")
            return new_issue.number

    except GithubException as e:
        print(f"GitHub API error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

if __name__ == '__main__':
    # Example usage (requires GITHUB_TOKEN and GITHUB_REPOSITORY to be set)
    # This part is for testing the script directly and should not run in production workflows as is.
    # Ensure GITHUB_REPOSITORY is like 'owner/repo'
    gh_repo = os.getenv('GITHUB_REPOSITORY')
    if gh_repo:
        print(f"Testing with repository: {gh_repo}")
        try:
            # Test case 1: Messages Log
            msg_issue_num = get_or_create_issue(gh_repo, "community-messages-log", "Community Messages Log")
            print(f"Messages Log Issue Number: #{msg_issue_num}")

            # Test case 2: Stories Log (will likely find the one created above if run quickly or use existing)
            story_issue_num = get_or_create_issue(gh_repo, "community-stories-log", "Community Stories Log")
            print(f"Stories Log Issue Number: #{story_issue_num}")

            # Test case 3: Trending Repos Log
            trending_issue_num = get_or_create_issue(gh_repo, "trending-repos-log", "Trending Repositories Log")
            print(f"Trending Repos Log Issue Number: #{trending_issue_num}")

        except Exception as e:
            print(f"Error during test: {e}")
    else:
        print("GITHUB_REPOSITORY environment variable not set. Skipping direct test.")
