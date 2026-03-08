from __future__ import annotations

from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import EmotionState, Parse
from soul.utils.util import clamp

logger = Logger(__name__)


class Emotion:
    def __init__(self) -> None:
        self.emotion_state = EmotionState()

    def describe(self) -> str:
        return (
            f"{self.emotion_state.label}"
            f"(愉悦 {self.emotion_state.valence:.2f}, "
            f"唤醒 {self.emotion_state.arousal:.2f}, "
            f"掌控 {self.emotion_state.dominance:.2f})"
        )

    @catch_and_log(logger)
    def update_emotion(self, parsed: Parse) -> None:
        sentiment_shift = {
            "positive": (0.08, 0.05, 0.02),
            "negative": (-0.10, 0.08, -0.04),
            "urgent": (-0.04, 0.15, 0.01),
            "neutral": (0.01, 0.00, 0.00),
        }
        delta_valence, delta_arousal, delta_dominance = sentiment_shift.get(
            parsed.sentiment, sentiment_shift["neutral"]
        )

        if parsed.intent in {"memory_save", "memory_query"}:
            delta_dominance += 0.03
        if parsed.intent.startswith("action_") or parsed.intent == "task_plan":
            delta_arousal += 0.05
        if parsed.importance_hint >= 0.75:
            delta_arousal += 0.05

        self.emotion_state.valence = clamp(self.emotion_state.valence + delta_valence)
        self.emotion_state.arousal = clamp(self.emotion_state.arousal + delta_arousal)
        self.emotion_state.dominance = clamp(
            self.emotion_state.dominance + delta_dominance
        )
        self._refresh_label()

    @catch_and_log(logger)
    def react_to_action_result(self, success: bool) -> None:
        if success:
            self.emotion_state.valence = clamp(self.emotion_state.valence + 0.04)
            self.emotion_state.dominance = clamp(self.emotion_state.dominance + 0.06)
        else:
            self.emotion_state.valence = clamp(self.emotion_state.valence - 0.05)
            self.emotion_state.dominance = clamp(self.emotion_state.dominance - 0.08)
            self.emotion_state.arousal = clamp(self.emotion_state.arousal + 0.03)
        self._refresh_label()

    @catch_and_log(logger)
    def heartbeat(self) -> None:
        # 心跳会把状态缓慢拉回基线，避免情绪长期饱和。
        self.emotion_state.valence += (0.52 - self.emotion_state.valence) * 0.06
        self.emotion_state.arousal += (0.45 - self.emotion_state.arousal) * 0.08
        self.emotion_state.dominance += (0.56 - self.emotion_state.dominance) * 0.05
        self.emotion_state.clamp()
        self._refresh_label()

    def _refresh_label(self) -> None:
        v = self.emotion_state.valence
        a = self.emotion_state.arousal
        if v >= 0.65 and a >= 0.62:
            self.emotion_state.label = "兴奋"
        elif v >= 0.62:
            self.emotion_state.label = "愉快"
        elif v <= 0.35 and a >= 0.58:
            self.emotion_state.label = "紧张"
        elif v <= 0.35:
            self.emotion_state.label = "低落"
        elif a <= 0.32:
            self.emotion_state.label = "松弛"
        else:
            self.emotion_state.label = "平静"

