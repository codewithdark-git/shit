import os
import re
import sys
from github import Github
import markdown
from datetime import datetime

def validate_message(content):
    # Check for basic markdown formatting
    if not content.strip().startswith('-'):
        print("Error: Message does not start with '-'.", file=sys.stderr)
        return False
    
    # Check for proper attribution format
    if not re.search(r'@[\w-]+', content):
        print("Error: Message does not contain proper attribution (e.g., @username).", file=sys.stderr)
        return False
    
    return True

def validate_story(content):
    # Check for minimum length
    if len(content.strip()) < 50:
        print("Error: Story is too short (minimum 50 characters).", file=sys.stderr)
        return False
    
    # Check for basic markdown formatting (expects a heading)
    if not re.search(r'^#{1,6}\s+.*', content.strip()):
        print("Error: Story does not start with a markdown heading (e.g., ## My Story).", file=sys.stderr)
        return False
    
    # Check for author attribution
    if not re.search(r'@[\w-]+', content):
        print("Error: Story does not contain proper author attribution (e.g., @username).", file=sys.stderr)
        return False
    
    return True

def process_messages():
    with open('MESSAGES.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ensure proper structure
    if '# Community Messages for the One Billionth Repo' not in content:
        content = '# Community Messages for the One Billionth Repo\n\n' + content
    
    if 'Add your message below!' not in content:
        content = content.replace('# Community Messages for the One Billionth Repo\n',
                                '# Community Messages for the One Billionth Repo\n\n'
                                'Add your message below!  \n'
                                '_You can add a PR or comment with your congratulations, jokes, or hopes for the future._\n\n---\n\n')
    
    # Sort messages
    messages = content.split('---\n\n')[1].strip().split('\n')
    messages = [m for m in messages if m.strip() and validate_message(m)]
    messages.sort()
    
    # Rebuild file
    header = content.split('---\n\n')[0] + '---\n\n'
    return header + '\n'.join(messages)

def process_stories():
    try:
        with open('STORIES.md', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = '''# GitHub Stories

Share your GitHub journey and experiences here! Add your story with a pull request.

## Guidelines
- Add a meaningful title for your story
- Include your GitHub handle
- Share something unique about your experience
- Keep it friendly and constructive

---

'''
    
    # Split into sections and validate
    sections = re.split(r'(?=##\s+)', content)
    header = sections[0]
    stories = sections[1:]
    
    # Sort stories by title
    stories = [s for s in stories if validate_story(s)]
    stories.sort(key=lambda x: re.search(r'##\s+(.*)', x).group(1).lower())
    
    return header + '\n'.join(stories)

def main():
    token = os.getenv('GITHUB_TOKEN')
    pr_number = int(os.getenv('PR_NUMBER'))
    repo_name = os.getenv('GITHUB_REPOSITORY')

    if not token or not pr_number or not repo_name:
        print("Error: Missing GITHUB_TOKEN, PR_NUMBER, or GITHUB_REPOSITORY environment variables.", file=sys.stderr)
        sys.exit(1)

    g = Github(token)
    try:
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
    except Exception as e:
        print(f"Error: Could not access GitHub repository or pull request: {e}", file=sys.stderr)
        sys.exit(1)

    files_changed = [f.filename for f in pr.get_files()]
    
    if 'MESSAGES.md' in files_changed:
        try:
            messages_file_content = repo.get_contents("MESSAGES.md", ref=pr.head.sha).decoded_content.decode('utf-8')
            # Extract messages after the '---' separator
            parts = messages_file_content.split('---\n\n', 1)
            if len(parts) > 1:
                individual_messages = parts[1].strip().split('\n')
                for msg in individual_messages:
                    msg = msg.strip()
                    if msg: # Process only non-empty lines
                        if not validate_message(msg):
                            print("Validation failed for MESSAGES.md", file=sys.stderr)
                            sys.exit(1)
            # If all validations pass, process the entire file for sorting and structuring
            processed_content = process_messages()
            with open('MESSAGES.md', 'w', encoding='utf-8') as f:
                f.write(processed_content)
        except Exception as e:
            print(f"Error processing MESSAGES.md: {e}", file=sys.stderr)
            sys.exit(1)

    if 'STORIES.md' in files_changed:
        try:
            stories_file_content = repo.get_contents("STORIES.md", ref=pr.head.sha).decoded_content.decode('utf-8')
            # Split stories: header part and then stories starting with '## '
            header_match = re.match(r'.*?---\n\n', stories_file_content, re.DOTALL)
            if header_match:
                header_part = header_match.group(0)
                stories_part = stories_file_content[len(header_part):]
            else: # Fallback if --- is not present, consider all content as stories part
                stories_part = stories_file_content

            individual_stories = re.split(r'(?=^##\s+)', stories_part, flags=re.MULTILINE)

            for story_content in individual_stories:
                story_content = story_content.strip()
                if story_content and not story_content.startswith("## Guidelines") and story_content != "# GitHub Stories": # Process actual story content
                    # Skip empty strings that may result from split if the content doesn't start with ##
                    if not story_content.startswith('## '):
                        continue
                    if not validate_story(story_content):
                        print("Validation failed for STORIES.md", file=sys.stderr)
                        sys.exit(1)

            # If all validations pass, process the entire file for sorting and structuring
            processed_content = process_stories()
            with open('STORIES.md', 'w', encoding='utf-8') as f:
                f.write(processed_content)
        except Exception as e:
            print(f"Error processing STORIES.md: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()
