import os
import requests
from datetime import datetime, timedelta
import pytz
import sys

# Adjust sys.path to find github_utils.py in .github/scripts
# Assumes update_trending.py is in src/ and github_utils.py is in .github/scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.github', 'scripts')))
from github_utils import get_or_create_issue
from github import Github # PyGithub

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') # This should already be set by the workflow
HEADERS = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}

# Constants for Trending Repos Log
TRENDING_LOG_LABEL = "trending-repos"
TRENDING_LOG_TITLE = "Trending Repositories"

def get_trending_repos():
    # Calculate date for repos created in the last week
    week_ago = (datetime.now(pytz.UTC) - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # GitHub Search API query
    query = f'created:>{week_ago} sort:stars-desc'
    url = f'https://api.github.com/search/repositories?q={query}&per_page=10'
    
    response = requests.get(url, headers=HEADERS)
    return response.json()['items']

def format_repo_entry(repo):
    stars = repo['stargazers_count']
    description = repo['description'] or 'No description provided'
    return f"- [{repo['full_name']}]({repo['html_url']}): {description} ⭐{stars}"

def update_public_repos_file():
    trending_repos_list = get_trending_repos() # Renamed for clarity
    
    # --- Post to GitHub Issue ---
    repo_name_env = os.getenv('GITHUB_REPOSITORY')
    trending_issue_obj = None

    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN not set. Skipping issue posting and MD update.", file=sys.stderr)
        return # Early exit if no token, as both issue posting and MD update might need it implicitly or explicitly

    if repo_name_env:
        try:
            g = Github(GITHUB_TOKEN) # Initialize PyGithub client
            trending_issue_number = get_or_create_issue(repo_name_env, TRENDING_LOG_LABEL, TRENDING_LOG_TITLE)
            trending_issue_obj = g.get_repo(repo_name_env).get_issue(number=trending_issue_number)
            print(f"Fetched trending repos log issue #{trending_issue_obj.number}")
        except Exception as e:
            print(f"Error getting or creating trending repos log issue: {e}", file=sys.stderr)
            # Continue without trending_issue_obj, MD file update will still proceed
    else:
        print("GITHUB_REPOSITORY environment variable not set. Skipping issue posting.", file=sys.stderr)

    if trending_issue_obj and trending_repos_list:
        comment_body_parts = [f"## 🔥 Trending Repositories - {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M UTC')}"]
        for repo_item in trending_repos_list: # Iterate through the list from get_trending_repos()
            comment_body_parts.append(format_repo_entry(repo_item)) # Use existing function

        final_comment = "\n".join(comment_body_parts)
        try:
            trending_issue_obj.create_comment(final_comment)
            print(f"Posted trending repos to issue #{trending_issue_obj.number}")
        except Exception as e:
            print(f"Error posting trending repos to issue #{trending_issue_obj.number}: {e}", file=sys.stderr)
    elif not trending_repos_list:
        print("No trending repositories found to post to issue.", file=sys.stderr)
    # --- End of Post to GitHub Issue ---

    # --- Update PUBLIC_REPOS.md (original functionality) ---
    if not trending_repos_list:
        print("No trending repositories found to update PUBLIC_REPOS.md.")
        # Optionally, decide if the MD file should be cleared or left as is.
        # For now, if no repos, it will effectively clear the trending section in MD.
    
    try:
        with open('PUBLIC_REPOS.md', 'r', encoding='utf-8') as f:
            content = f.read()

        trending_section_header = '## Trending\n'
        # Ensure trending_repos_list is used here as well
        trending_entries = '\n'.join(format_repo_entry(repo) for repo in trending_repos_list)

        parts = content.split('## Trending')
        if len(parts) >= 2:
            # This logic assumes the "## Trending" header exists and is followed by other "## " sections.
            # It tries to preserve content after the trending list up to the next "## "
            intro_part = parts[0]
            # Content after "## Trending" header
            after_trending_header_part = parts[1]

            # Find where the old list of trending items ends (i.e., before the next "## " section or EOF)
            next_section_marker_match = re.search(r"(\n##\s)", after_trending_header_part, re.MULTILINE)
            if next_section_marker_match:
                # There's another section after the trending list
                following_content = after_trending_header_part[next_section_marker_match.start():]
            else:
                # Trending list is the last major section, or only section.
                following_content = "" # No other major sections after it.

            new_content = intro_part + trending_section_header + trending_entries + following_content
        else:
            # "## Trending" section not found, append it. This might be too simple.
            # A better approach might be to ensure a placeholder exists or use a more robust template.
            print("'## Trending' section not found in PUBLIC_REPOS.md. Appending new section.", file=sys.stderr)
            new_content = content.rstrip('\n') + '\n\n' + trending_section_header + trending_entries + '\n'

        with open('PUBLIC_REPOS.md', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Updated PUBLIC_REPOS.md with new trending repositories.")
    except Exception as e:
        print(f"Error updating PUBLIC_REPOS.md: {e}", file=sys.stderr)


if __name__ == '__main__':
    update_public_repos_file()
# Ensure re is imported at the top if used.
