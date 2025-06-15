import os
import re
import sys
from github import Github
import markdown
from datetime import datetime

# Add .github/scripts to sys.path to find github_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from github_utils import get_or_create_issue

# Constants for Messages Log
MESSAGES_LOG_LABEL = "community-messages"
MESSAGES_LOG_TITLE = "Community Messages"

# Constants for Stories Log
STORIES_LOG_LABEL = "community-stories"
STORIES_LOG_TITLE = "Community Stories"

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
    token = os.getenv('ACCESS_TOKEN')
    if not token: 
        print("Error: Missing GITHUB_TOKEN.", file=sys.stderr)
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
            messages_issue = None
            try:
                messages_issue_number = get_or_create_issue(repo_name, MESSAGES_LOG_LABEL, MESSAGES_LOG_TITLE)
                messages_issue = repo.get_issue(number=messages_issue_number)
                print(f"Fetched messages log issue #{messages_issue.number}")
            except Exception as e:
                print(f"Error getting or creating messages log issue: {e}", file=sys.stderr)
                # Continue to update MD file even if issue posting fails for now

            # Extract messages after the '---' separator
            parts = messages_file_content.split('---\n\n', 1)
            if len(parts) > 1:
                individual_messages = parts[1].strip().split('\n')
                all_messages_valid = True # Flag to track validation status
                valid_messages_for_posting = [] # Store messages that pass validation

                for msg_content in individual_messages:
                    msg_content = msg_content.strip()
                    if msg_content: # Process only non-empty lines
                        if not validate_message(msg_content):
                            print(f"Validation failed for message: \"{msg_content}\" in MESSAGES.md", file=sys.stderr)
                            all_messages_valid = False
                            # Do not exit immediately, report all validation errors for the file if any.
                        else:
                            # Store valid messages if we need to post them later
                            # This assumes we only post if ALL messages in the PR are valid.
                            # Or, we could post them one by one here.
                            # For now, let's collect them and post after all are validated.
                            valid_messages_for_posting.append(msg_content)

                if not all_messages_valid:
                    print("Validation failed for one or more messages in MESSAGES.md. No messages will be posted to the issue. MD file will not be updated.", file=sys.stderr)
                    sys.exit(1) # Exit if any message validation fails

                # If all messages are valid, then proceed to post them
                if messages_issue and all_messages_valid: # all_messages_valid is redundant here due to sys.exit(1) above, but good for clarity
                    pr_author = pr.user.login
                    for valid_msg in valid_messages_for_posting:
                        try:
                            comment_body = f"New message from PR #{pr.number} by @{pr_author}:\n\n{valid_msg}"
                            messages_issue.create_comment(comment_body)
                            print(f"Posted message to issue #{messages_issue.number}: {valid_msg}")
                        except Exception as e:
                            print(f"Error posting message to issue #{messages_issue.number}: {e}", file=sys.stderr)

            # If all validations pass (implicit due to potential sys.exit(1) above), process the entire file for sorting and structuring
            processed_content = process_messages()
            with open('MESSAGES.md', 'w', encoding='utf-8') as f:
                f.write(processed_content)
        except Exception as e:
            print(f"Error processing MESSAGES.md: {e}", file=sys.stderr)
            sys.exit(1)

    if 'STORIES.md' in files_changed:
        try:
            stories_file_content = repo.get_contents("STORIES.md", ref=pr.head.sha).decoded_content.decode('utf-8')
            stories_issue = None
            try:
                stories_issue_number = get_or_create_issue(repo_name, STORIES_LOG_LABEL, STORIES_LOG_TITLE)
                stories_issue = repo.get_issue(number=stories_issue_number)
                print(f"Fetched stories log issue #{stories_issue.number}")
            except Exception as e:
                print(f"Error getting or creating stories log issue: {e}", file=sys.stderr)
                # Continue to update MD file even if issue posting fails for now

            header_match = re.match(r'.*?---\n\n', stories_file_content, re.DOTALL)
            if header_match:
                header_part = header_match.group(0) # Includes the ---
                stories_text_block = stories_file_content[len(header_part):]
            else: # Fallback if --- is not present, or if content starts directly with stories.
                  # This assumes the Guideline/Intro part might not have '---' if it's very simple.
                intro_end_match = re.match(r'(# GitHub Stories\n+(## Guidelines\n.*?\n)?)(?=^##\s+)', stories_file_content, re.DOTALL | re.MULTILINE)
                if intro_end_match:
                    stories_text_block = stories_file_content[len(intro_end_match.group(1)):]
                else: # If no clear intro, assume all are stories or story-like content
                    stories_text_block = stories_file_content

            individual_stories_from_file = re.split(r'(?=^##\s+)', stories_text_block, flags=re.MULTILINE)

            all_stories_valid = True
            valid_stories_for_posting = []

            for story_content_full in individual_stories_from_file:
                story_content_clean = story_content_full.strip()

                # Skip empty parts or known non-story sections if they weren't filtered by split logic
                if not story_content_clean or \
                   story_content_clean.startswith("## Guidelines") or \
                   (story_content_clean == "# GitHub Stories" and "# GitHub Stories" in header_part): # Avoid re-validating title if it was part of header
                    continue

                # Ensure it actually starts like a story heading, protects against random text blocks
                if not story_content_clean.startswith('## '):
                    continue

                if not validate_story(story_content_clean): # validate_story expects a full story including its "## Title"
                    print(f"Validation failed for a story in STORIES.md (content starts with: \"{story_content_clean[:50]}...\")", file=sys.stderr)
                    all_stories_valid = False
                    # Continue checking other stories to list all errors if desired, or break if one error is enough.
                    # Current validate_story prints specific errors. This general message is also helpful.
                else:
                    valid_stories_for_posting.append(story_content_clean)

            if not all_stories_valid:
                print("Validation failed for one or more stories in STORIES.MD. No stories will be posted. MD file will not be updated.", file=sys.stderr)
                sys.exit(1)

            if stories_issue and all_stories_valid: # all_stories_valid is redundant due to sys.exit(1)
                pr_author = pr.user.login
                for story_to_post in valid_stories_for_posting:
                    try:
                        comment_body = f"New story from PR #{pr.number} by @{pr_author}:\n\n---\n\n{story_to_post}\n\n---"
                        stories_issue.create_comment(comment_body)
                        print(f"Posted story to issue #{stories_issue.number} (content starts with: \"{story_to_post[:50]}...\")")
                    except Exception as e:
                        print(f"Error posting story to issue #{stories_issue.number}: {e}", file=sys.stderr)

            processed_content = process_stories()
            with open('STORIES.md', 'w', encoding='utf-8') as f:
                f.write(processed_content)
        except Exception as e:
            print(f"Error processing STORIES.md: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()
