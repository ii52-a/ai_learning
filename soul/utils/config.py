from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = BASE_DIR / "runtime"
MEMORY_FILE = RUNTIME_DIR / "memory.json"
STATE_FILE = RUNTIME_DIR / "agent_state.json"
TASKS_FILE = RUNTIME_DIR / "tasks.json"
SCREENSHOT_DIR = RUNTIME_DIR / "screenshots"
BG_FILE = BASE_DIR / "utils" / "bg.txt"


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class InitConfig:
    IF_LLM_PARSE: bool = _env_flag("SOUL_ENABLE_LLM_PARSE", False)
    IF_LLM_RESPOND: bool = _env_flag("SOUL_ENABLE_LLM_RESPOND", True)
    TOOL_AGENT_ENABLED: bool = _env_flag("SOUL_TOOL_AGENT_ENABLED", True)
    MAX_TOOL_ROUNDS: int = int(os.getenv("SOUL_MAX_TOOL_ROUNDS", "4"))
    HEARTBEAT_INTERVAL_SECONDS: float = float(os.getenv("SOUL_HEARTBEAT_INTERVAL", "2.5"))
    MAX_SHORT_TERM_MEMORIES: int = int(os.getenv("SOUL_MAX_SHORT_TERM", "12"))
    COMPRESSION_WINDOW: int = int(os.getenv("SOUL_COMPRESSION_WINDOW", "6"))
    MAX_LONG_TERM_MEMORIES: int = int(os.getenv("SOUL_MAX_LONG_TERM", "40"))
    MAX_IMPORTANT_EVENTS: int = int(os.getenv("SOUL_MAX_IMPORTANT", "20"))
    SHORT_TERM_EXPIRE_HOURS: float = float(os.getenv("SOUL_SHORT_TERM_EXPIRE_HOURS", "8"))
    LONG_TERM_FORGET_DAYS: int = int(os.getenv("SOUL_LONG_TERM_FORGET_DAYS", "14"))
    IMPORTANT_FORGET_DAYS: int = int(os.getenv("SOUL_IMPORTANT_FORGET_DAYS", "45"))
    COMPUTER_CONTROL_ENABLED: bool = _env_flag("SOUL_COMPUTER_CONTROL_ENABLED", True)
    PERCEPTION_ENABLED: bool = _env_flag("SOUL_PERCEPTION_ENABLED", True)
    AUTO_EXECUTE_TASKS: bool = _env_flag("SOUL_AUTO_EXECUTE_TASKS", True)
    AUTO_RESUME_TASKS: bool = _env_flag("SOUL_AUTO_RESUME_TASKS", False)
    ACTIVE_MODEL_ALIAS: str = os.getenv("SOUL_MODEL_ALIAS", "").strip()
    DEFAULT_PROVIDER: str = os.getenv("SOUL_MODEL_PROVIDER", "").strip().lower()
    DEFAULT_MODEL_NAME: str = os.getenv("SOUL_MODEL_NAME", "").strip()

    def ensure_runtime(self) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    def load_background_prompt(self) -> str:
        if not BG_FILE.exists():
            return ""
        return BG_FILE.read_text(encoding="utf-8").strip()
