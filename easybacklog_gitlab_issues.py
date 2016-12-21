import urllib3
import json
import os

EASYBACKLOG_SECRET = os.environ.get("EASYBACKLOG_SECRET", "XXXXX")
GITLAB_SECRET = os.environ.get("GITLAB_SECRET", "XXXXX")

urllib3.disable_warnings()
http = urllib3.PoolManager()


def get_sprint_stories(sprint_id):
    r = http.request(
        "GET",
        "https://easybacklog.com/api/sprints/%s/sprint-stories" % sprint_id,
        headers={
            "Authorization": "token %s" % EASYBACKLOG_SECRET
        })
    stories = []
    for story_id in json.loads(r.data):
        r = http.request(
            "GET",
            "https://easybacklog.com/api/stories/%s" % story_id[
                'story_id'],
            headers={
                "Authorization": "token %s" % EASYBACKLOG_SECRET
            })
        stories.append(json.loads(r.data))
    return stories


def get_theme_stories(theme_id):
    r = http.request(
        "GET",
        "https://easybacklog.com/api/themes/%s/stories" % theme_id,
        headers={
            "Authorization": "token %s" % EASYBACKLOG_SECRET
        })
    return json.loads(r.data)


def get_backlog_stories(backlog_id):
    themes = get_project_themes(backlog_id)
    stories = []
    for theme in themes:
        stories += get_theme_stories(theme["id"])
    return stories


def get_project_themes(backlog_id):
    r = http.request(
        "GET",
        "https://easybacklog.com/api/backlogs/%s/themes/" % backlog_id,
        headers={
            "Authorization": "token %s" % EASYBACKLOG_SECRET
        })
    return json.loads(r.data)


def add_stories_to_gitlab(stories, backlog_id, gitlab_project_id):
    """
    Get user stories from easybacklog and
    add them to Gitlab as gitlab issues
    Author: Nader Alexan
    """
    for story_data in stories:
        # Get theme name
        r = http.request(
            "GET",
            "https://easybacklog.com/api/backlogs/%s/themes/%s/" % (
                backlog_id, story_data["theme_id"]),
            headers={
                "Authorization": "token %s" % EASYBACKLOG_SECRET
            })
        theme = json.loads(r.data)
        # Generate issue title
        issue_title = "[%s] %s" % (theme["name"], formulate_issue_title(story_data))

        r = http.request(
            "GET",
            "https://easybacklog.com/api/stories/%s/acceptance-criteria" % story_data[
                'id'],
            headers={
                "Authorization": "token %s" % EASYBACKLOG_SECRET
            })
        description = "Acceptance Criteria: %s\n" % json.loads(r.data)
        description += "Comments: %s" % story_data["comments"]

        # Check if issue is already in Gitlab issues
        issues = []
        page_num = 1
        while True:
            r = http.request(
                "GET",
                "https://gitlab.com/api/v3/projects/%s/issues?page=%d" % (
                    gitlab_project_id, page_num),
                headers={
                    "PRIVATE-TOKEN": GITLAB_SECRET,
                    "Content-Type": "application/json"
                }
            )
            new_issues = json.loads(r.data)
            issues += new_issues
            if not new_issues:
                break
            page_num += 1

        found = False
        for issue in issues:
            if issue_title.strip() == issue["title"].strip():
                found = True
                break

        if not found:
            # Add issue to gitlab
            print("ADDED: %s" % issue_title)
            r = http.request(
                "POST",
                "https://gitlab.com/api/v3/projects/%s/issues" % gitlab_project_id,
                headers={
                    "PRIVATE-TOKEN": GITLAB_SECRET,
                    "Content-Type": "application/json"
                },
                body=json.dumps({
                    "id": gitlab_project_id,
                    "title": issue_title,
                    "description": description
                }).encode('utf-8')
            )


def formulate_issue_title(story):
    return "As a %s I want to %s so I can %s" % (
        story["as_a"],
        story["i_want_to"],
        story["so_i_can"]
    )
def main():
    level = ""
    while(not level):
        level = raw_input(
            """
You want to get stories at which level:
1. Backlog
2. Theme
3. Sprint
Your choice: """)
        if level not in ["1", "2", "3"]:
            level = ""
            print("Please enter a valid choice")
    backlog_id = raw_input("Enter backlog id: ")
    functions = {
        "1": (get_backlog_stories, ""),
        "2": (get_theme_stories, "Enter theme id: "),
        "3": (get_sprint_stories, "Enter sprint id: ")
    }
    function, input_string = functions[level]
    if input_string:
        _id = raw_input(input_string)
    else:
        _id = backlog_id
    stories = function(_id)
    print("Retrieved %d stories from easybacklog" % len(stories))
    view = raw_input("View all stories? (y/N)")
    if view == "y":
        for story in stories:
            print formulate_issue_title(story)
    add = raw_input("Add stories to gitlab? (y/N)")
    if add == "y":
        gitlab_project_id = raw_input("Enter gitlab project id: ")
        add_stories_to_gitlab(stories, backlog_id, gitlab_project_id)
        print("Done")


if __name__ == "__main__":
    main()
