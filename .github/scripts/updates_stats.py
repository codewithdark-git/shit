from github import Github
import os
import datetime
import json
from pathlib import Path
import sys
# Add the repository root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.github_api import GitHubAPI

def update_readme_stats(stats, content):
    stats_section = f"""## 📊 Repository Stats
- ⭐ Stars: {stats['stars']}
- 🍴 Forks: {stats['forks']}
- 📬 Open Issues: {stats['issues']}
- 👀 Watchers: {stats['watchers']}
- 📅 Last Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
"""
    return content.replace("## 📊 Repository Stats\n", stats_section)

def update_trending_section(trending_repos, content):
    trending_section = "### 🔥 Trending Repositories\n"
    for repo in trending_repos[:5]:
        trending_section += f"- [{repo['full_name']}]({repo['html_url']}): {repo['description']} ⭐{repo['stargazers_count']}\n"
    
    return content.replace("### 🔥 Trending Repositories\n", trending_section)

def update_language_section(language_stats, content):
    language_section = "### 🎨 By Programming Language\n"
    for lang, stats in sorted(language_stats.items(), key=lambda x: x[1]['stars'], reverse=True)[:5]:
        language_section += f"- {lang}: {stats['count']} repositories, {stats['stars']} total stars\n"
    
    return content.replace("### 🎨 By Programming Language\n", language_section)

def main():
    # Initialize API clients
    github_token = os.environ['GITHUB_TOKEN']
    g = Github(github_token)
    api = GitHubAPI(github_token)
    
    # Get repository stats
    repo = g.get_repo("AasishPokhrel/shit")
    stats = {
        'stars': repo.stargazers_count,
        'forks': repo.forks_count,
        'issues': repo.open_issues_count,
        'watchers': repo.watchers_count
    }
    
    # Get trending repositories
    trending_repos = api.get_trending_repos(since="weekly")
    
    # Get language statistics
    language_stats = api.get_language_stats()
    
    # Get topic statistics
    topics = ["ai", "web-development", "mobile", "devops", "security"]
    topic_stats = api.get_topic_stats(topics)
    
    # Update README
    with open('README.md', 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = update_readme_stats(stats, content)
    content = update_trending_section(trending_repos.get('items', []), content)
    content = update_language_section(language_stats, content)
    
    with open('README.md', 'w', encoding='utf-8') as file:
        file.write(content)
    
    # Save detailed stats for historical tracking
    stats_dir = Path('.github/stats')
    stats_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    stats_file = stats_dir / f'stats_{timestamp}.json'
    
    full_stats = {
        'repository': stats,
        'trending': trending_repos,
        'languages': language_stats,
        'topics': topic_stats,
        'timestamp': timestamp
    }
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(full_stats, f, indent=2)

if __name__ == "__main__":
    main()
