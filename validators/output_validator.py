import re
from dataclasses import dataclass, field
from schemas.plan_schema import PlanSchema


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        if self.errors:
            lines.append("ERRORS:")
            lines.extend(f"  ✗ {e}" for e in self.errors)
        if self.warnings:
            lines.append("WARNINGS:")
            lines.extend(f"  ⚠ {w}" for w in self.warnings)
        if self.passed:
            lines.append("  ✅ All validation checks passed")
        return "\n".join(lines)


class OutputValidator:
    """
    Structural validation of generated game files.
    Three layers — all Python, no LLM, no execution environment needed.

    Layer 1: File existence — all 3 files present and non-empty
    Layer 2: Syntax markers — basic structural integrity checks
    Layer 3: Coherence — files reference each other correctly, framework used properly
    """

    def validate(self, files: dict[str, str], plan: PlanSchema) -> ValidationResult:
        errors = []
        warnings = []

        # ── Layer 1: File Existence ───────────────────────────────────────────
        for filename in ["index.html", "style.css", "game.js"]:
            content = files.get(filename, "")
            if not content or len(content.strip()) < 50:
                errors.append(f"Layer 1: '{filename}' is missing or suspiciously short")

        if errors:
            return ValidationResult(passed=False, errors=errors, warnings=warnings)

        html = files["index.html"]
        css = files["style.css"]
        js = files["game.js"]

        # ── Layer 2: Syntax Markers ───────────────────────────────────────────

        # HTML checks
        if "<!DOCTYPE html>" not in html and "<!doctype html>" not in html.lower():
            warnings.append("Layer 2: index.html missing DOCTYPE declaration")

        if "<canvas" not in html and plan.framework == "vanilla":
            errors.append("Layer 2: index.html missing <canvas> element (required for vanilla JS)")

        if not re.search(r"<script", html, re.IGNORECASE):
            errors.append("Layer 2: index.html has no <script> tag")

        if "game.js" not in html:
            errors.append("Layer 2: index.html does not load game.js")

        # CSS checks
        if len(css.strip()) < 10:
            warnings.append("Layer 2: style.css is nearly empty")

        # JS checks
        if len(js) < 200:
            errors.append("Layer 2: game.js is suspiciously short — likely incomplete")

        # Check for TODO or placeholder markers in JS
        todo_matches = re.findall(r"(TODO|PLACEHOLDER|FIXME|NOT IMPLEMENTED)", js, re.IGNORECASE)
        if todo_matches:
            warnings.append(f"Layer 2: game.js contains unfinished markers: {set(todo_matches)}")

        # Check JS ends properly (not truncated)
        js_stripped = js.rstrip()
        if js_stripped and js_stripped[-1] not in ("}", ";", ")"):
            warnings.append("Layer 2: game.js may be truncated (doesn't end with } ; or )")

        # ── Layer 3: Coherence ────────────────────────────────────────────────

        # Framework coherence
        if plan.framework == "phaser":
            if "phaser" not in html.lower():
                errors.append("Layer 3: Plan says 'phaser' but index.html doesn't load Phaser CDN")
            if "phaser" not in js.lower() and "Scene" not in js:
                warnings.append("Layer 3: Plan says 'phaser' but game.js has no Phaser Scene usage")
        elif plan.framework == "vanilla":
            if "phaser" in html.lower():
                warnings.append("Layer 3: Plan says 'vanilla' but index.html loads Phaser — may be intentional")

        # State machine coherence
        for state in plan.state_machine:
            # Check if each state is at least mentioned somewhere in game.js
            if state.lower() not in js.lower():
                warnings.append(f"Layer 3: State '{state}' from plan not found in game.js")

        # Controls coherence
        for key in plan.controls:
            key_variants = [key, key.replace("Arrow", ""), key.lower()]
            if not any(k in js for k in key_variants):
                warnings.append(f"Layer 3: Control key '{key}' from plan not found in game.js")

        passed = len(errors) == 0
        return ValidationResult(passed=passed, errors=errors, warnings=warnings)