from collections import defaultdict

class DataProcessor:
    def __init__(self, config):
        self.size_categories = config.size_categories
        self.projects_per_category = config.projects_per_category
        self.projects = {lang: defaultdict(list) for lang in config.languages}

    def get_size_category(self, lines_of_code):
        """Determine the size category based on lines of code."""
        for category, (min_lines, max_lines) in self.size_categories.items():
            if min_lines <= lines_of_code <= max_lines:
                return category
        return None

    def get_remaining_counts(self, language):
        """Calculate how many more projects are needed for each size category."""
        remaining = {}
        for category in self.size_categories:
            current_count = len(self.projects[language][category])
            remaining[category] = max(0, self.projects_per_category - current_count)
        return remaining