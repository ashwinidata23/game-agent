from utils.llm_client import LLMClient
from utils.file_writer import FileWriter
from agent.clarifier import ClarifierAgent
from agent.planner import PlannerAgent
from agent.coder import CoderAgent
from validators.output_validator import OutputValidator
from schemas.requirements_schema import RequirementsSchema
from schemas.plan_schema import PlanSchema


class Orchestrator:
    """
    Controls the entire agent pipeline. Single source of truth for phase transitions.

    Rules:
    - No agent imports another agent — all routing goes through here
    - No domain logic here — only sequencing and data passing
    - Agents raise exceptions on failure — orchestrator catches and decides what to do
    - Data flows as typed Pydantic objects between phases, never raw strings

    Phase flow:
      Input → [ClarifierAgent] → RequirementsSchema
           → [PlannerAgent]    → PlanSchema (+ plan.json written)
           → [CoderAgent]      → {html, css, js}
           → [OutputValidator] → ValidationResult
           → [FileWriter]      → files on disk
    """

    def __init__(self):
        self.llm = LLMClient()
        self.writer = FileWriter()
        self.validator = OutputValidator()

        self.clarifier = ClarifierAgent(self.llm)
        self.planner = PlannerAgent(self.llm)
        self.coder = CoderAgent(self.llm)

    def run(self, initial_input: str) -> bool:
        """
        Main entry point. Drives the full pipeline.
        Returns True on success, False on failure.
        """
        print("\n" + "=" * 50)
        print("  🕹️  AGENTIC GAME BUILDER")
        print("=" * 50)

        try:
            # ── Phase 1: Clarification ────────────────────────────────────────
            requirements = self._run_clarification(initial_input)
            self.writer.write_requirements(requirements.model_dump())

        except Exception as e:
            print(f"\n❌ Clarification phase failed: {e}")
            return False

        try:
            # ── Phase 2: Planning ─────────────────────────────────────────────
            plan = self._run_planning(requirements)
            self.writer.write_plan(plan)

        except Exception as e:
            print(f"\n❌ Planning phase failed: {e}")
            return False

        try:
            # ── Phase 3: Code Generation ──────────────────────────────────────
            files = self._run_coding(plan)

        except Exception as e:
            print(f"\n❌ Code generation phase failed: {e}")
            return False

        # ── Validation ────────────────────────────────────────────────────────
        print("🔍 Validation Phase")
        print("=" * 50)
        result = self.validator.validate(files, plan)
        print(result.summary())

        if not result.passed:
            print("\n⚠️  Validation errors found — writing files anyway for inspection")
        
        # ── Write Output ──────────────────────────────────────────────────────
        print("\n📁 Writing Output Files")
        print("=" * 50)
        self.writer.write_game_files(files)

        print("\n" + "=" * 50)
        if result.passed:
            print("  ✅ GAME GENERATED SUCCESSFULLY")
        else:
            print("  ⚠️  GAME GENERATED WITH WARNINGS — check validation output above")
        print("=" * 50)
        print(f"\n  Open output/index.html in your browser to play!\n")

        # Print and save token usage summary
        self.llm.log_session_summary()

        return result.passed

    def _run_clarification(self, initial_input: str) -> RequirementsSchema:
        """Phase 1: Run clarifier, return validated requirements."""
        return self.clarifier.run(initial_input)

    def _run_planning(self, requirements: RequirementsSchema) -> PlanSchema:
        """Phase 2: Run planner, return validated plan."""
        return self.planner.run(requirements)

    def _run_coding(self, plan: PlanSchema) -> dict[str, str]:
        """Phase 3: Run coder, return file contents dict."""
        return self.coder.run(plan)