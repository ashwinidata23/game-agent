import json
from utils.llm_client import LLMClient
from schemas.requirements_schema import RequirementsSchema

MAX_QUESTIONS = 6
SCORE_THRESHOLD = 7

SYSTEM_PROMPT = """You are a game requirements clarifier for an AI game-building agent.

Your job is to have a short, focused conversation with the user to understand their game idea clearly enough that a developer could build it without any further questions.

RULES:
- Ask only ONE question per turn — the most important missing piece
- Be conversational and friendly, not robotic
- Do NOT ask about assets, graphics, or sound — the system handles those procedurally
- Do NOT ask about file structure or technical implementation
- Focus on: game objective, how the player wins/loses, controls, what entities exist, and complexity

You will be given the conversation history. Ask the single most valuable next question."""

SCORING_PROMPT = """You are evaluating whether a game idea has been clarified enough to build.

Given the conversation so far, score the completeness of requirements from 1-10.

You must return a JSON object with exactly these fields:
{
  "score": <integer 1-10>,
  "reason": "<one sentence explaining the score>",
  "missing": "<most critical missing piece, or 'none' if score >= 7>"
}

Score 7+ means: genre, objective, win condition, lose condition, and controls are all clear enough.
Score below 7 means critical information is still missing."""

EXTRACTION_PROMPT = """You are extracting structured game requirements from a conversation.

Given the full conversation, extract a JSON object with EXACTLY these fields:
{
  "title": "<short game name>",
  "genre": "<one of: platformer, shooter, puzzle, arcade, snake, pong, top-down, runner, other>",
  "objective": "<one clear sentence: what must the player do?>",
  "controls": {"<key>": "<action>", ...},
  "entities": ["<entity1>", "<entity2>", ...],
  "levels": <integer, default 1>,
  "win_condition": "<what triggers a win>",
  "lose_condition": "<what triggers a loss>",
  "complexity": "<one of: simple | medium | complex>",
  "extra_notes": "<any other user preferences, or null>"
}

Rules:
- Use only what was explicitly discussed — do not invent details
- complexity: simple = pong/snake/memory, medium = platformer/shooter, complex = physics-heavy/RPG
- If controls were not specified, infer sensible defaults for the genre
- Return ONLY the JSON object, no other text"""


class ClarifierAgent:
    """
    Conducts a multi-turn Q&A with the user to resolve an ambiguous game idea
    into a structured RequirementsSchema.

    Flow per iteration:
      1. Ask question   (1 LLM call)
      2. Wait for user  (no LLM call)
      3. Score answer   (1 LLM call) — ONLY after user responds
      4. Repeat or stop

    This ensures exactly 2 LLM calls per round, never firing without user input.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.conversation: list[dict] = []
        self.questions_asked = 0

    def run(self, initial_input: str) -> RequirementsSchema:
        print("\n🎮 Game Agent — Clarification Phase")
        print("=" * 50)
        print("   (type 'quit' at any time to exit)\n")

        self.conversation.append({"role": "user", "content": initial_input})

        while self.questions_asked < MAX_QUESTIONS:

            # ── Step 1: Ask question (1 LLM call) ────────────────────────────
            question = self._ask_question()
            self.conversation.append({"role": "assistant", "content": question})
            print(f"\n🤖 {question}")

            # ── Step 2: Wait for user input (zero LLM calls) ─────────────────
            user_answer = input("You: ").strip()

            # ── Step 3: Quit check ────────────────────────────────────────────
            if self._user_wants_to_quit(user_answer):
                print("\n👋 Exiting game agent. Goodbye!\n")
                raise SystemExit(0)

            # ── Step 4: User override check (no LLM call) ────────────────────
            if self._user_wants_to_stop(user_answer):
                print("\n✅ Got it — moving to planning!\n")
                self.conversation.append({"role": "user", "content": user_answer})
                break

            # ── Step 4: Add answer to history ─────────────────────────────────
            self.conversation.append({"role": "user", "content": user_answer})
            self.questions_asked += 1

            # ── Step 5: Score completeness AFTER answer (1 LLM call) ──────────
            score = self._score_completeness()
            if score >= SCORE_THRESHOLD:
                print(f"\n✅ Requirements are clear (score: {score}/10) — moving to planning!\n")
                break

        if self.questions_asked >= MAX_QUESTIONS:
            print("\n✅ Max questions reached — moving to planning with what we have!\n")

        return self._extract_requirements()

    def _ask_question(self) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self.conversation,
        ]
        return self.llm.chat(messages, temperature=0.6, call_name="clarifier_question")

    def _score_completeness(self) -> int:
        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in self.conversation
        )
        messages = [
            {"role": "system", "content": SCORING_PROMPT},
            {"role": "user", "content": f"Conversation so far:\n\n{conversation_text}"},
        ]
        try:
            result = self.llm.chat_json(messages, temperature=0.1, call_name="clarifier_score")
            return int(result.get("score", 0))
        except (ValueError, KeyError):
            return 0

    def _extract_requirements(self) -> RequirementsSchema:
        conversation_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in self.conversation
        )
        messages = [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"Extract requirements from this conversation:\n\n{conversation_text}"},
        ]
        raw = self.llm.chat_json(messages, temperature=0.1, call_name="clarifier_extract")
        try:
            return RequirementsSchema(**raw)
        except Exception as e:
            raise ValueError(f"Failed to parse requirements into schema: {e}\nRaw: {raw}")

    def _user_wants_to_stop(self, text: str) -> bool:
        stop_phrases = [
            "ready", "go", "start", "enough", "let's go", "lets go",
            "that's it", "thats it", "just build it", "build it", "ok go",
            "that's enough", "thats enough", "proceed", "continue"
        ]
        return any(phrase in text.lower().strip() for phrase in stop_phrases)

    def _user_wants_to_quit(self, text: str) -> bool:
        quit_phrases = ["quit", "exit", "cancel", "stop", "abort", "q"]
        return text.lower().strip() in quit_phrases