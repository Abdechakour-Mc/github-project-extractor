import os
from github_project_extractor.config import Config
from github_project_extractor.extractor import GitHubProjectExtractor

def main():
    config = Config("config.json")
    github_token = os.environ.get("GITHUB_TOKEN",)
    
    if not github_token:
        print("Please set your GitHub API token as an environment variable GITHUB_TOKEN")
        exit(1)

    extractor = GitHubProjectExtractor(github_token, config)
    extractor.run()

if __name__ == "__main__":
    main()