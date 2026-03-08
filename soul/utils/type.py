from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4


MemoryKind = Literal["user", "assistant", "summary", "event", "reflection", "system"]
ActionType = Literal[
    "none",
    "open_app",
    "open_url",
    "search_web",
    "run_command",
    "type_text",
    "hotkey",
    "capture_screen",
    "inspect_screen",
    "list_windows",
    "focus_window",
    "list_processes",
    "list_dir",
    "read_file",
    "write_file",
    "create_dir",
    "click",
    "scroll",
]
TaskStatus = Literal["pending", "running", "completed", "failed", "skipped"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EmotionState:
    valence: float = 0.5
    arousal: float = 0.45
    dominance: float = 0.55
    label: str = "平静"

    def clamp(self) -> None:
        self.valence = min(max(self.valence, 0.0), 1.0)
        self.arousal = min(max(self.arousal, 0.0), 1.0)
        self.dominance = min(max(self.dominance, 0.0), 1.0)


@dataclass
class PersonalityProfile:
    name: str = "多伦娜"
    identity: str = "一位20岁花季的淑女，喜欢交际，为人直接"
    style: str = "直接、温和、会记住重要事情"
    warmth: float = 0.68
    directness: float = 0.72
    curiosity: float = 0.60
    patience: float = 0.82
    courage: float = 0.58


@dataclass
class Entity:
    type: str
    value: str


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: uuid4().hex[:10])


@dataclass
class ModelResponse:
    content: str
    provider: str
    model: str
    raw: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"


@dataclass
class ModelProfile:
    alias: str
    provider: str
    model: str
    base_url: str = ""
    api_key_env: str = ""
    supports_vision: bool = False
    enabled: bool = True


@dataclass
class ActionRequest:
    action_type: ActionType = "none"
    target: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    requires_confirmation: bool = False
    confidence: float = 0.70


@dataclass
class Parse:
    text: str
    subject: str = ""
    object: str = ""
    intent: str = "chat"
    entities: list[Entity] = field(default_factory=list)
    sentiment: str = "neutral"
    importance_hint: float = 0.4
    asks_memory: bool = False
    action: ActionRequest = field(default_factory=ActionRequest)


@dataclass
class ParseError(Parse):
    text: str = "Parse Error"
    subject: str = "unknown"
    object: str = "unknown"
    intent: str = "error"


@dataclass
class MemoryItem:
    content: str
    kind: MemoryKind
    timestamp: str = field(default_factory=lambda: utc_now().isoformat())
    importance: float = 0.5
    emotional_weight: float = 0.5
    tags: list[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed_at: Optional[str] = None
    summary: str = ""
    source: str = "conversation"
    memory_id: str = field(default_factory=lambda: uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryItem":
        return cls(**payload)


@dataclass
class MemorySnapshot:
    short_term: list[MemoryItem] = field(default_factory=list)
    long_term: list[MemoryItem] = field(default_factory=list)
    important_events: list[MemoryItem] = field(default_factory=list)
    last_compacted_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "short_term": [item.to_dict() for item in self.short_term],
            "long_term": [item.to_dict() for item in self.long_term],
            "important_events": [item.to_dict() for item in self.important_events],
            "last_compacted_at": self.last_compacted_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemorySnapshot":
        return cls(
            short_term=[MemoryItem.from_dict(item) for item in payload.get("short_term", [])],
            long_term=[MemoryItem.from_dict(item) for item in payload.get("long_term", [])],
            important_events=[
                MemoryItem.from_dict(item) for item in payload.get("important_events", [])
            ],
            last_compacted_at=payload.get("last_compacted_at"),
        )


@dataclass
class HeartbeatSnapshot:
    total_beats: int
    bpm: int
    uptime_seconds: float
    last_beat_at: str


@dataclass
class ScreenSnapshot:
    captured_at: str
    screenshot_path: str = ""
    screen_size: tuple[int, int] = (0, 0)
    active_window: str = ""
    visible_windows: list[str] = field(default_factory=list)
    ocr_excerpt: str = ""


@dataclass
class TaskStep:
    title: str
    instruction: str
    action: ActionRequest = field(default_factory=ActionRequest)
    status: TaskStatus = "pending"
    result: str = ""
    step_id: str = field(default_factory=lambda: uuid4().hex[:8])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPlan:
    goal: str
    steps: list[TaskStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: utc_now().isoformat())
    source: str = "local"
    plan_id: str = field(default_factory=lambda: uuid4().hex[:8])

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at,
            "source": self.source,
            "plan_id": self.plan_id,
        }

