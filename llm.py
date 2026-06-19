import anthropic
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import csv

from config import globalVar

# initialise the shared tracker if not already set
if not hasattr(globalVar, "llm_cost_tracker") or globalVar.llm_cost_tracker is None:
    globalVar.llm_cost_tracker = {}


# ── Config ────────────────────────────────────────────────────────────────────
from utils.utils import json_parser

# open_router_config = json_parser(Path("open-router-api-key.json"))
open_router_config = json_parser(Path("open-router-api-key.json"))
OPENROUTER_API_KEY = open_router_config["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = open_router_config["OPENROUTER_BASE_URL"]


# ── Pricing (per 1M tokens, USD) ──────────────────────────────────────────────
MODEL_PRICING = {
    # model_id: (input, output, cache_write, cache_read)
    "anthropic/claude-sonnet-4-6": (3.00, 15.00, 3.75, 0.30),
    "anthropic/claude-opus-4-6": (15.00, 75.00, 18.75, 1.50),
    "anthropic/claude-haiku-3-5": (0.80, 4.00, 1.00, 0.08),
    "openai/gpt-4o": (5.00, 15.00, 0.00, 0.00),
    "openai/gpt-4o-mini": (0.15, 0.60, 0.00, 0.00),
    "openai/o3-mini": (1.10, 4.40, 0.00, 0.00),
    "google/gemini-pro-1.5": (3.50, 10.50, 0.00, 0.00),
    "google/gemini-flash-1.5": (0.35, 1.05, 0.00, 0.00),
    "meta-llama/llama-3.1-70b-instruct": (0.59, 0.79, 0.00, 0.00),
    "meta-llama/llama-3.1-405b-instruct": (5.32, 5.32, 0.00, 0.00),
    "mistralai/mistral-large": (3.00, 9.00, 0.00, 0.00),
    "mistralai/mistral-small": (0.20, 0.60, 0.00, 0.00),
    "deepseek/deepseek-chat": (0.27, 1.10, 0.00, 0.00),
    "deepseek/deepseek-r1": (0.55, 2.19, 0.00, 0.00),
}

# ── Log file path ─────────────────────────────────────────────────────────────
CALL_LOG_PATH = Path("logs/token_calls.csv")


# ── Usage record ──────────────────────────────────────────────────────────────
@dataclass
class UsageRecord:
    model: str
    called_by: str
    input_tokens: int
    output_tokens: int
    system: str = ""
    user_input: str = ""
    output: str = ""
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# ── Helpers for globalVar.llm_cost_tracker ────────────────────────────────────


def _tracker_bucket(called_by: str) -> dict:
    """Return (creating if needed) the cost bucket for `called_by`."""
    if called_by not in globalVar.llm_cost_tracker:
        globalVar.llm_cost_tracker[called_by] = {
            "calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_write_tokens": 0,
            "cache_read_tokens": 0,
            "cost_usd": 0.0,
        }
    return globalVar.llm_cost_tracker[called_by]


def _update_global_tracker(record: UsageRecord):
    """Add one record's usage into the shared globalVar bucket."""
    bucket = _tracker_bucket(record.called_by)
    bucket["calls"] += 1
    bucket["input_tokens"] += record.input_tokens
    bucket["output_tokens"] += record.output_tokens
    bucket["cache_write_tokens"] += record.cache_write_tokens
    bucket["cache_read_tokens"] += record.cache_read_tokens
    bucket["cost_usd"] += record.cost_usd


def global_cumsum_usd() -> float:
    """Total cost across ALL agents/instances in this process."""
    return sum(b["cost_usd"] for b in globalVar.llm_cost_tracker.values())


# ── Token tracker ─────────────────────────────────────────────────────────────
class TokenTracker:
    """
    Tracks token usage for one LLMCenter instance.

    Per-call log  → CALL_LOG_PATH (CSV, one row per call, persistent)
    In-memory     → self.records  (this instance only)
    Global cumsum → globalVar.llm_cost_tracker (all instances, keyed by called_by)
    """

    CALL_LOG_HEADERS = [
        "timestamp",
        "called_by",
        "model",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cache_write_tokens",
        "cache_read_tokens",
        "cost_usd",
        "system",
        "user_input",
        "output",
    ]

    def __init__(self, call_log: Path = CALL_LOG_PATH):
        self.records: list[UsageRecord] = []
        self.call_log = Path(call_log)
        self._init_files()

    def _init_files(self):
        self.call_log.parent.mkdir(parents=True, exist_ok=True)
        if not self.call_log.exists():
            with self.call_log.open("w", newline="") as f:
                csv.DictWriter(f, fieldnames=self.CALL_LOG_HEADERS).writeheader()

    def _calc_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int,
        cache_read_tokens: int,
    ) -> float:
        prices = MODEL_PRICING.get(model)
        if not prices:
            return 0.0
        in_p, out_p, cw_p, cr_p = prices
        return (
            (input_tokens / 1_000_000) * in_p
            + (output_tokens / 1_000_000) * out_p
            + (cache_write_tokens / 1_000_000) * cw_p
            + (cache_read_tokens / 1_000_000) * cr_p
        )

    def track(
        self,
        model: str,
        called_by: str,
        usage,
        system: str = "",
        user_input: str = "",
        output: str = "",
    ) -> UsageRecord:
        """
        Record one API call's usage.
        Appends to the CSV and updates globalVar.llm_cost_tracker.
        """

        def get(attr, default=0):
            return (
                getattr(usage, attr, None)
                or (usage.get(attr, default) if isinstance(usage, dict) else default)
                or default
            )

        input_tokens = get("input_tokens")
        output_tokens = get("output_tokens")
        cache_write_tokens = get("cache_creation_input_tokens")
        cache_read_tokens = get("cache_read_input_tokens")
        cost = self._calc_cost(
            model, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens
        )

        record = UsageRecord(
            model=model,
            called_by=called_by,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_write_tokens=cache_write_tokens,
            cache_read_tokens=cache_read_tokens,
            cost_usd=cost,
            system=system,
            user_input=user_input,
            output=output,
        )
        self.records.append(record)
        _update_global_tracker(record)
        self._write_call_log(record)
        return record

    def _write_call_log(self, record: UsageRecord):
        with self.call_log.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CALL_LOG_HEADERS)
            writer.writerow(
                {
                    "timestamp": record.timestamp,
                    "called_by": record.called_by,
                    "model": record.model,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_tokens": record.total_tokens,
                    "cache_write_tokens": record.cache_write_tokens,
                    "cache_read_tokens": record.cache_read_tokens,
                    "cost_usd": f"{record.cost_usd:.8f}",
                    "system": record.system,
                    "user_input": record.user_input,
                    "output": record.output,
                }
            )

    def summary(self, verbose: bool = True) -> dict:
        """
        Prints per-agent breakdown from globalVar and the global cumsum.
        """
        tracker = globalVar.llm_cost_tracker
        if not tracker:
            print("No usage recorded yet.")
            return {}

        cumsum = global_cumsum_usd()

        if verbose:
            total_calls = sum(b["calls"] for b in tracker.values())
            total_input = sum(b["input_tokens"] for b in tracker.values())
            total_output = sum(b["output_tokens"] for b in tracker.values())

            print("\n" + "═" * 60)
            print(f"  TOKEN USAGE SUMMARY  ({total_calls} total calls)")
            print("═" * 60)
            print(f"  {'Input tokens':<28} {total_input:>10,}")
            print(f"  {'Output tokens':<28} {total_output:>10,}")
            print(f"  {'Total cost (all agents)':<28} ${cumsum:>12.6f}")
            print(f"  {'Call log':<28} {self.call_log}")
            print("─" * 60)
            print(f"\n  Per-agent breakdown:")
            for agent, b in tracker.items():
                label = agent if agent else "(unnamed)"
                print(f"\n  [{label}]  {b['calls']} call(s)  cost=${b['cost_usd']:.6f}")
                print(f"    input={b['input_tokens']:,}  output={b['output_tokens']:,}")
                if b["cache_write_tokens"] or b["cache_read_tokens"]:
                    print(
                        f"    cache_write={b['cache_write_tokens']:,}  cache_read={b['cache_read_tokens']:,}"
                    )
            print("═" * 60 + "\n")

        return {
            "total_cost_usd": cumsum,
            "by_agent": dict(globalVar.llm_cost_tracker),
        }

    def reset(self):
        self.records.clear()


# ── LLM Center ────────────────────────────────────────────────────────────────
class LLMCenter:
    """Handles all API calls. No task or agent logic here."""

    MODELS = {
        "claude-sonnet": "anthropic/claude-sonnet-4-6",
        "claude-opus": "anthropic/claude-opus-4-6",
        "claude-haiku": "anthropic/claude-haiku-3-5",
        "gpt-4o": "openai/gpt-4o",
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "o3-mini": "openai/o3-mini",
        "gemini-pro": "google/gemini-pro-1.5",
        "gemini-flash": "google/gemini-flash-1.5",
        "llama-70b": "meta-llama/llama-3.1-70b-instruct",
        "llama-405b": "meta-llama/llama-3.1-405b-instruct",
        "mistral-large": "mistralai/mistral-large",
        "mistral-small": "mistralai/mistral-small",
        "deepseek-chat": "deepseek/deepseek-chat",
        "deepseek-r1": "deepseek/deepseek-r1",
    }

    def __init__(
        self,
        called_by: str = "",
        api_key: str = OPENROUTER_API_KEY,
        base_url: str = OPENROUTER_BASE_URL,
        max_tokens: int = 8192,
        tracker: Optional[TokenTracker] = None,
    ):
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.max_tokens = max_tokens
        self.called_by = called_by
        self.tracker = tracker or TokenTracker()

    def resolve_model(self, model: str) -> str:
        return self.MODELS.get(model, model)

    def _print_record(self, record: UsageRecord):
        short = record.model.split("/")[-1]
        bucket = _tracker_bucket(record.called_by)
        parts = [
            f"agent={record.called_by or '(unnamed)'}",
            f"model={short}",
            f"in={record.input_tokens}",
            f"out={record.output_tokens}",
        ]
        if record.cache_write_tokens:
            parts.append(f"cache_write={record.cache_write_tokens}")
        if record.cache_read_tokens:
            parts.append(f"cache_read={record.cache_read_tokens}")
        parts.append(f"cost=${record.cost_usd:.6f}")
        parts.append(f"agent_total=${bucket['cost_usd']:.6f}")
        parts.append(f"global_total=${global_cumsum_usd():.6f}")
        print(f"  ↳ {' | '.join(parts)}")

    def complete(self, model: str, system: str, user_input: str) -> str:
        resolved = self.resolve_model(model)
        response = self.client.messages.create(
            model=resolved,
            max_tokens=self.max_tokens,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user_input}],
        )
        output = response.content[0].text
        record = self.tracker.track(
            resolved,
            self.called_by,
            response.usage,
            system=system,
            user_input=user_input,
            output=output,
        )
        self._print_record(record)
        return output

    def stream(self, model: str, system: str, user_input: str) -> str:
        resolved = self.resolve_model(model)
        full_text = []

        with self.client.messages.stream(
            model=resolved,
            max_tokens=self.max_tokens,
            system=[
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": user_input}],
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                full_text.append(text)
            usage = stream.get_final_message().usage

        print()
        output = "".join(full_text)
        record = self.tracker.track(
            resolved,
            self.called_by,
            usage,
            system=system,
            user_input=user_input,
            output=output,
        )
        self._print_record(record)
        return output


# ── Shared instances ──────────────────────────────────────────────────────────
tracker = TokenTracker()
llmCenter = LLMCenter(
    called_by="default",
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
    tracker=tracker,
)


# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agent_a = LLMCenter(called_by="agent_a", tracker=tracker)
    agent_b = LLMCenter(called_by="agent_b", tracker=tracker)

    result1 = agent_a.complete("claude-sonnet", "You are helpful.", "Hello!")
    print(f"agent_a Claude: {result1}\n")

    result2 = agent_b.complete("gpt-4o", "You are helpful.", "Hello!")
    print(f"agent_b GPT: {result2}\n")

    result3 = agent_a.complete("claude-haiku", "You are helpful.", "What is 2+2?")
    print(f"agent_a Haiku: {result3}\n")

    tracker.summary()
