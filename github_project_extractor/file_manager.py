import json
import os

class FileManager:
    def __init__(self, output_file):
        self.output_file = output_file

    def load_existing_projects(self):
        """Load existing projects from the output file if it exists."""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r") as f:
                    data = json.load(f)
                return data.get("projects", {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading from existing file: {e}")
        return {}

    def save_progress(self, projects, metadata):
        """Save the current progress to the JSON file."""
        output = {"metadata": metadata, "projects": projects}
        with open(self.output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Saved progress to {self.output_file}")