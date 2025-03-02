import json
import os

class Config:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from the JSON file."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        with open(self.config_file, "r") as f:
            return json.load(f)

    @property
    def size_categories(self):
        return self.config.get("size_categories", {})

    @property
    def projects_per_category(self):
        return self.config.get("projects_per_category", 30)

    @property
    def languages(self):
        return self.config.get("languages", ["java", "python"])

    @property
    def search_parameters(self):
        return self.config.get("search_parameters", {
            "min_stars": 10,
            "created_range": "2015-01-01..2020-01-01",
            "last_pushed": "<2020-12-31"
        })

    @property
    def target_year(self):
        return self.config.get("target_year", 2020)  # Default to 2020 if not specified

    @property
    def output_file(self):
        return self.config.get("output_file", "github_projects.json")