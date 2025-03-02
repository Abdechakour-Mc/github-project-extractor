import base64
from datetime import datetime
import time
from .api_client import APIClient
from .data_processor import DataProcessor
from .file_manager import FileManager

class GitHubProjectExtractor:
    def __init__(self, token, config):
        self.token = token
        self.config = config
        self.api_client = APIClient(token)
        self.data_processor = DataProcessor(config)
        self.file_manager = FileManager(config.output_file)
        self.processed_repos = set()
        
    def get_last_commit_date(self, repo_name):
        """
        Get the date of the last commit to the repository.
        
        Args:
            repo_name (str): Repository name in owner/repo format
            
        Returns:
            str: Date of the last commit in ISO format
        """
        url = f"https://api.github.com/repos/{repo_name}/commits"
        params = {"per_page": 1}
        commits =  self.api_client.make_request(url, params)
        
        if commits and len(commits) > 0:
            return commits[0]['commit']['committer']['date']
        
        return None

    def _is_last_commit_before(self, last_commit_date):
        """
        Check if the last commit was before the target year.
        
        Args:
            last_commit_date (str): ISO format date string
            
        Returns:
            bool: True if the last commit was before the target year, False otherwise
        """
        if not last_commit_date:
            return False
            
        try:
            commit_year = int(last_commit_date.split('-')[0])
            return commit_year < self.config.target_year  # Use target_year from config
        except (IndexError, ValueError):
            return False

    def _count_lines_of_code(self, repo_name, language):
        """
        Count lines of code in a repository for a specific language.
        
        Args:
            repo_name (str): Repository name in owner/repo format
            language (str): Programming language to count lines for
            
        Returns:
            int: Total lines of code
        """
        
        # Set timeout limit
        start_time = time.time()
        timeout_seconds = 30
        
        # Get the default branch name
        default_branch = self._get_default_branch(repo_name)
        
        # Use the recursive tree API to get all files in the repository
        url = f"https://api.github.com/repos/{repo_name}/git/trees/{default_branch}?recursive=1"
        tree_data = self.api_client.make_request(url)
        
        if tree_data is None or 'tree' not in tree_data:
            return 0
        
        extensions = {
            "java": [".java"],
            "python": [".py", ".pyx", ".pyw"]
        }
        
        total_lines = 0
        language_extensions = extensions.get(language.lower(), [])
        
        for item in tree_data['tree']:
            # Check if we've exceeded the timeout
            if time.time() - start_time > timeout_seconds:
                print(f"Timeout reached for {repo_name}, skipping...")
                return 0
                
            if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in language_extensions):
                file_lines = self._count_file_lines(repo_name, item['path'])
                total_lines += file_lines
        return total_lines

    def _count_file_lines(self, repo_name, file_path):
        """
        Count lines in a specific file.
        
        Args:
            repo_name (str): Repository name in owner/repo format
            file_path (str): Path to the file in the repository
            
        Returns:
            int: Number of lines in the file
        """
        url = f"https://api.github.com/repos/{repo_name}/contents/{file_path}"
        file_data = self.api_client.make_request(url)
        
        if file_data is None or 'content' not in file_data:
            return 0
        
        try:
            content = base64.b64decode(file_data['content']).decode('utf-8')
            return len(content.splitlines())
        except Exception as e:
            print(f"Error decoding file {file_path}: {e}")
            return 0

    def _check_language_dominance(self, repo_name, target_language):
        """
        Check if the target language is the dominant language in the repository.
        
        Args:
            repo_name (str): Repository name in owner/repo format
            target_language (str): Target programming language
            
        Returns:
            bool: True if the target language is dominant, False otherwise
        """
        languages = self.api_client.make_request(f"https://api.github.com/repos/{repo_name}/languages")
        
        if not languages:
            return False
        
        # Calculate total bytes of code
        total_bytes = sum(languages.values())
        
        # Find the target language (case insensitive)
        target_bytes = 0
        for lang, bytes_count in languages.items():
            if lang.lower() == target_language.lower():
                target_bytes = bytes_count
                break
        
        # Check if the target language is dominant (more than 70% of the codebase)
        return (target_bytes / total_bytes) > 0.7

    def _get_default_branch(self, repo_name):
        """
        Get the default branch name for a repository.
        
        Args:
            repo_name (str): Repository name in owner/repo format
            
        Returns:
            str: Default branch name (e.g., 'main' or 'master')
        """
        url = f"https://api.github.com/repos/{repo_name}"
        repo_info = self.api_client.make_request(url)
        
        if repo_info and 'default_branch' in repo_info:
            return repo_info['default_branch']
        
        return 'master'  # Fallback to 'master' if not found

    def _process_repo(self, repo, language, remaining_counts):
        """Process a single repository."""
        repo_name = repo['full_name']
        if repo_name in self.processed_repos:
            return

        last_commit_date = self.get_last_commit_date(repo_name)
        if not self._is_last_commit_before(last_commit_date):  # No need to pass target_year
            return

        if not self._check_language_dominance(repo_name, language):
            return
        print(repo_name, '||||||||||')
        lines_of_code = self._count_lines_of_code(repo_name, language)
        print(lines_of_code, '||||||||||')
        size_category = self.data_processor.get_size_category(lines_of_code)

        if size_category is None or remaining_counts[size_category] <= 0:
            return

        self._add_project(repo, language, size_category, lines_of_code, remaining_counts)

    def _add_project(self, repo, language, size_category, lines_of_code, remaining_counts):
        """Add a project to the collection."""
        project_info = {
            "name": repo['name'],
            "full_name": repo['full_name'],
            "url": repo['html_url'],
            "api_url": repo['url'],
            "description": repo['description'],
            "stars": repo['stargazers_count'],
            "forks": repo['forks_count'],
            "language": language,
            "size_category": size_category,
            "lines_of_code": lines_of_code,
            "contributors_count": len(self.api_client.make_request(f"https://api.github.com/repos/{repo['full_name']}/contributors", params={"per_page": 100}) or []),
            "created_at": repo['created_at'],
            "last_commit_date": self.api_client.make_request(f"https://api.github.com/repos/{repo['full_name']}/commits", params={"per_page": 1})[0]['commit']['committer']['date'],
            "is_archived": repo.get('archived', False),
            "is_fork": repo['fork']
        }

        self.data_processor.projects[language][size_category].append(project_info)
        remaining_counts[size_category] -= 1
        self.processed_repos.add(repo['full_name'])
        self._save_progress()

    def _save_progress(self):
        """Save progress after each new project."""
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "projects_per_category": self.config.projects_per_category,
            "size_categories": self.config.size_categories,
            "languages": self.config.languages
        }
        self.file_manager.save_progress(self.data_processor.projects, metadata)

    def _save_final_progress(self):
        """Save final progress and print statistics."""
        self._save_progress()
        total_projects = sum(len(projects) for lang_projects in self.data_processor.projects.values() for projects in lang_projects.values())
        print(f"Extraction complete. Collected a total of {total_projects} projects:")
        for language in self.data_processor.projects:
            for category in self.config.size_categories:
                count = len(self.data_processor.projects[language][category])
                print(f"- {language} ({category}): {count}/{self.config.projects_per_category}")

    def run(self):
        """Run the full extraction process."""
        for language in self.config.languages:
            self.collect_projects(language)
        self._save_final_progress()

    def collect_projects(self, language):
        """Collect projects for a specific language."""
        remaining_counts = self.data_processor.get_remaining_counts(language)
        print(f"Collecting {language} projects... Remaining to collect: {remaining_counts}")

        if all(count == 0 for count in remaining_counts.values()):
            print(f"Already have {self.config.projects_per_category} projects for all {language} categories. Skipping.")
            return

        page = 1
        max_pages = 50

        while any(count > 0 for count in remaining_counts.values()) and page <= max_pages:
            print(f"Searching page {page}... Remaining to collect: {remaining_counts}")
            search_results = self.api_client.make_request(
                "https://api.github.com/search/repositories",
                params={
                    "q": f"language:{language} stars:>={self.config.search_parameters['min_stars']} "
                         f"created:{self.config.search_parameters['created_range']} "
                        #  f"pushed:{self.config.search_parameters['last_pushed']} fork:false archived:false",
                         f"pushed:{self.config.search_parameters['last_pushed']} fork:false archived:false",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page
                }
            )

            if not search_results or 'items' not in search_results:
                print(f"No more {language} repositories found or reached the end of results.")
                break

            for repo in search_results['items']:
                self._process_repo(repo, language, remaining_counts)

            page += 1
            time.sleep(2)