import os
import json
from schemas.plan_schema import PlanSchema


OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")


class FileWriter:
    """
    Writes all output files to the output directory.
    Output directory is mounted as a Docker volume so files persist on host.
    """

    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def write_game_files(self, files: dict[str, str]) -> None:
        """Write index.html, style.css, game.js to output directory."""
        for filename, content in files.items():
            path = os.path.join(self.output_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            size_kb = len(content.encode("utf-8")) / 1024
            print(f"   📄 {filename} ({size_kb:.1f} KB) → {path}")

    def write_plan(self, plan: PlanSchema) -> None:
        """Write plan.json to output directory — visible artifact of the planning phase."""
        path = os.path.join(self.output_dir, "plan.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))
        print(f"   📋 plan.json → {path}")

    def write_requirements(self, reqs_dict: dict) -> None:
        """Write resolved requirements JSON — visible artifact of clarification phase."""
        path = os.path.join(self.output_dir, "requirements.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(reqs_dict, f, indent=2)
        print(f"   📋 requirements.json → {path}")