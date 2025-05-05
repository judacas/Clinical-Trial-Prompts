import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, Optional, Tuple

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError, RateLimitError

from .config import DEFAULT_OUTPUT_DIR, MAX_CONCURRENT_OPENAI_CALLS

# ---------------------------------------------------------------------------
# -----------------------  CONFIGURABLE CONSTANTS  --------------------------
# ---------------------------------------------------------------------------
TPM_LIMIT = 2_000_000  # tokens‑per‑minute org quota (GPT‑4‑class)
RPM_LIMIT = 10_000  # requests‑per‑minute org quota

MAX_RETRIES = 3  # retries per call on RateLimitError
WAIT_AFTER_429 = 15  # seconds

SCHEMA_PAD_EXTRA = 5  # small constant to avoid fencepost issues
PRED_COMPLETION_RATIO = 5  # prompt:completion  ≈ 5:1  (conservative)


timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

METRICS_DIR = Path(DEFAULT_OUTPUT_DIR) / "metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)

CALLS_METRICS_FILE = METRICS_DIR / f"clinical_trial_calls_{timestamp}.jsonl"

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# -------------------------  RATE LIMIT BUCKETS  ----------------------------
# ---------------------------------------------------------------------------
class _RollingBucket:
    """60‑second sliding‑window counter for tokens or requests."""

    def __init__(self, capacity: int, name: str):
        self.capacity = capacity
        self.name = name
        self._records: Deque[Tuple[float, int]] = deque()
        self._cond = threading.Condition()

    def _trim(self) -> int:
        now = time.time()
        while self._records and now - self._records[0][0] >= 60:
            self._records.popleft()
        return sum(cost for _, cost in self._records)

    def wait(self, cost: int):
        with self._cond:
            while True:
                used = self._trim()
                if used + cost <= self.capacity:
                    self._records.append((time.time(), cost))
                    return
                oldest_ts = self._records[0][0]
                sleep_for = max(0.05, 60 - (time.time() - oldest_ts))
                self._cond.wait(timeout=sleep_for)

    def commit(self, actual: int):
        with self._cond:
            if self._records:
                self._records.pop()
            self._records.append((time.time(), actual))
            self._cond.notify_all()


token_bucket = _RollingBucket(TPM_LIMIT, "TPM")
request_bucket = _RollingBucket(RPM_LIMIT, "RPM")

# ---------------------------------------------------------------------------
# ----------------------  GLOBAL 429 PAUSE HANDLER  -------------------------
# ---------------------------------------------------------------------------
_pause_event = threading.Event()
_last_429_ts = 0.0
_pause_lock = threading.Lock()


def _handle_rate_limit_error():
    global _last_429_ts
    with _pause_lock:
        _last_429_ts = time.time()
        _pause_event.set()
        logger.warning(
            "Rate limit hit. Pausing all threads for %s seconds", WAIT_AFTER_429
        )


def _wait_if_paused():
    while _pause_event.is_set():
        with _pause_lock:
            remaining = (_last_429_ts + WAIT_AFTER_429) - time.time()
            if remaining <= 0:
                _pause_event.clear()
                break
        time.sleep(min(remaining, 0.1))


# ---------------------------------------------------------------------------
# --------------------------  LOGGING HELPERS  ------------------------------
# ---------------------------------------------------------------------------

_calls_lock = threading.Lock()

# ---------------------------------------------------------------------------
# -------------------------  TOKEN COUNT UTILS  -----------------------------
# ---------------------------------------------------------------------------
_enc_cache: Dict[str, tiktoken.Encoding] = {}


def _enc(model: str):
    if model not in _enc_cache:
        # _enc_cache[model] = tiktoken.encoding_for_model(model)
        try:

            _enc_cache[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            _enc_cache[model] = tiktoken.get_encoding("o200k_base")
            # looks like 4.1 hasn't been implemented yet but everyone assumes it uses this one
            # https://github.com/openai/tiktoken/issues/395
    return _enc_cache[model]


def _count_tokens(text: str, model: str):
    return len(_enc(model).encode(text))


# ---------------------------------------------------------------------------
# --------------------------  OPENAI CLIENT  --------------------------------
# ---------------------------------------------------------------------------
load_dotenv()


def get_openai_client() -> OpenAI:
    """
    Initialize and return an OpenAI client configured with the appropriate API key.

    This function loads the API key from environment variables and creates a
    properly configured OpenAI client for use throughout the application.

    Returns:
        OpenAI: The initialized OpenAI client.

    Raises:
        ValueError: If the OPENAI_API_KEY is not found in environment variables.
    """
    # Retrieve API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")

    # Verify API key existence
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    logger.info("OpenAI client initialized.")

    # Create and return the OpenAI client
    return OpenAI(api_key=api_key)


openAI_client = get_openai_client()
api_semaphore = threading.Semaphore(MAX_CONCURRENT_OPENAI_CALLS)

# ---------------------------------------------------------------------------
# ---------------------  PER‑CALL METRIC WRITER  ----------------------------
# ---------------------------------------------------------------------------


def _log_call(**entry):
    with _calls_lock:
        with CALLS_METRICS_FILE.open("a") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")


# shortcut for errors


def _record_error(err_type: str, **kwargs):
    entry = {"ts": time.time(), "error": err_type, **kwargs}
    _log_call(**entry)
    logger.error(
        "OpenAI error %s | prompt=%d schema=%d",
        err_type,
        kwargs.get("prompt_tokens"),
        kwargs.get("schema_tokens"),
    )


# ---------------------------------------------------------------------------
# ---------------------  PUBLIC WRAPPER FUNCTION  ---------------------------
# ---------------------------------------------------------------------------


def tracked_openai_completion_call(
    *,
    model: str,
    messages,
    response_format,
    temperature: float = 0.0,
    timeout: Optional[int] = None,
):
    """Thread‑safe quota‑aware OpenAI call using static semaphore."""

    prompt_tokens = sum(_count_tokens(m["content"], model) for m in messages)
    schema_str = json.dumps(response_format.model_json_schema(), separators=(",", ":"))
    schema_tokens = _count_tokens(schema_str, model)
    pred_completion = max(1, (prompt_tokens + schema_tokens) // PRED_COMPLETION_RATIO)
    cost_pred = prompt_tokens + schema_tokens + pred_completion + SCHEMA_PAD_EXTRA

    _wait_if_paused()

    token_bucket.wait(cost_pred)
    request_bucket.wait(1)

    start_time = time.perf_counter()
    for attempt in range(1, MAX_RETRIES + 1):
        with api_semaphore:
            try:
                completion = openAI_client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                    timeout=timeout,
                )
                break
            except RateLimitError:
                token_bucket.commit(0)
                request_bucket.commit(0)
                _record_error(
                    "RateLimitError",
                    retry=attempt - 1,
                    prompt_tokens=prompt_tokens,
                    schema_tokens=schema_tokens,
                    pred_completion=pred_completion,
                    completion_tokens=0,
                )
                _handle_rate_limit_error()
                if attempt == MAX_RETRIES:
                    raise
                _wait_if_paused()
                token_bucket.wait(cost_pred)
                request_bucket.wait(1)
                continue
            except OpenAIError as e:
                token_bucket.commit(0)
                request_bucket.commit(0)
                _record_error(
                    type(e).__name__,
                    retry=attempt - 1,
                    prompt_tokens=prompt_tokens,
                    schema_tokens=schema_tokens,
                    pred_completion=pred_completion,
                    completion_tokens=0,
                )
                raise e
    else:
        raise RuntimeError("Max retries exhausted")

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    if usage := completion.usage or None:
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens
        prompt_cached = (
            usage.prompt_tokens_details.cached_tokens or 0
            if usage.prompt_tokens_details
            else 0
        )
    else:
        # Fallback in case usage is not available for some reason
        logger.warning("No usage info in OpenAI response")
        completion_tokens = 0
        total_tokens = 0
        prompt_cached = 0
    token_bucket.commit(total_tokens)
    request_bucket.commit(1)

    # per‑call log
    _log_call(
        ts=time.time(),
        retry=(attempt - 1),
        prompt_tokens=prompt_tokens,
        schema_tokens=schema_tokens,
        pred_completion=pred_completion,
        completion_tokens=completion_tokens,
        prompt_cached=prompt_cached,
        total_tokens=total_tokens,
        lat_ms=round(latency_ms, 1),
        sem_capacity=MAX_CONCURRENT_OPENAI_CALLS,
        error=None,
    )
    logger.info(
        "OpenAI call OK | tokens=%d (+schema %d) completion=%d latency=%.1fms",
        prompt_tokens,
        schema_tokens,
        completion_tokens,
        latency_ms,
    )

    return completion
