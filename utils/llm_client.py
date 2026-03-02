import os
import json
import logging
from datetime import datetime
from openai import OpenAI

# Token usage logger — writes to both console and token_usage.log in output dir
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(os.path.join(OUTPUT_DIR, "token_usage.log")),
        logging.StreamHandler(),
    ],
)
token_logger = logging.getLogger("token_usage")


class LLMClient:
    """
    Single wrapper for all OpenAI API calls.
    Uses gpt-4o-mini for clarification + planning (fast, cheap).
    Uses gpt-4o for code generation (powerful, follows complex prompts).
    Tracks token usage per call and session total, logs to token_usage.log.
    """

    PRICING = {
        "gpt-4o":      {"input": 0.005,   "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    }

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY environment variable not set.")
        self.client = OpenAI(api_key=api_key)

        self.model_fast  = "gpt-4o"  # set same as smart for reliability
        self.model_smart = "gpt-4o"

        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.total_cost = 0.0
        self.session_start = datetime.now()

        token_logger.info(f"\n{'='*50}")
        token_logger.info(f"  TOKEN USAGE LOG — {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        token_logger.info(f"  Clarifier/Planner : {self.model_fast}")
        token_logger.info(f"  Coder             : {self.model_smart}")
        token_logger.info(f"{'='*50}")

    def _log_usage(self, call_name: str, usage, model: str):
        inp   = usage.prompt_tokens
        out   = usage.completion_tokens
        total = usage.total_tokens
        pricing = self.PRICING.get(model, self.PRICING["gpt-4o"])
        cost = (inp / 1000 * pricing["input"]) + (out / 1000 * pricing["output"])
        self.total_input_tokens  += inp
        self.total_output_tokens += out
        self.total_calls += 1
        self.total_cost  += cost
        token_logger.info(
            f"[Call #{self.total_calls}] {call_name} ({model}) | "
            f"in: {inp} | out: {out} | total: {total} | ~${cost:.4f}"
        )

    def log_session_summary(self):
        total_tokens = self.total_input_tokens + self.total_output_tokens
        duration = (datetime.now() - self.session_start).seconds
        token_logger.info(f"\n{'='*50}")
        token_logger.info(f"  SESSION SUMMARY")
        token_logger.info(f"{'='*50}")
        token_logger.info(f"  Total API calls  : {self.total_calls}")
        token_logger.info(f"  Input tokens     : {self.total_input_tokens:,}")
        token_logger.info(f"  Output tokens    : {self.total_output_tokens:,}")
        token_logger.info(f"  Total tokens     : {total_tokens:,}")
        token_logger.info(f"  Estimated cost   : ~${self.total_cost:.4f}")
        token_logger.info(f"  Duration         : {duration}s")
        token_logger.info(f"{'='*50}\n")

    def chat(self, messages, temperature=0.7, max_tokens=4096,
             call_name="chat", use_smart_model=False) -> str:
        model = self.model_smart if use_smart_model else self.model_fast
        response = self.client.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens,
        )
        self._log_usage(call_name, response.usage, model)
        return response.choices[0].message.content.strip()

    def chat_json(self, messages, temperature=0.3, max_tokens=2048,
                  call_name="chat_json", use_smart_model=False) -> dict:
        model = self.model_smart if use_smart_model else self.model_fast
        response = self.client.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        self._log_usage(call_name, response.usage, model)
        raw = response.choices[0].message.content.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output:\n{raw}")