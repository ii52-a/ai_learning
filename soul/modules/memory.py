from __future__ import annotations

import json
from pathlib import Path

from soul.utils.config import InitConfig, MEMORY_FILE
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import EmotionState, MemoryItem, MemorySnapshot, Parse
from soul.utils.util import days_since, extract_keywords, hours_since, utc_now_iso

logger = Logger(__name__)


class Memory:
    def __init__(self, storage_path: Path | None = None, config: InitConfig | None = None):
        self.config = config or InitConfig()
        self.config.ensure_runtime()
        self.storage_path = Path(storage_path or MEMORY_FILE)
        self.snapshot = self._load()

    def recall(self, query: str = "", limit: int = 5) -> list[MemoryItem]:
        candidates = (
            self.snapshot.short_term
            + self.snapshot.long_term
            + self.snapshot.important_events
        )
        if not candidates:
            return []

        keywords = set(extract_keywords(query))
        ranked: list[tuple[float, MemoryItem]] = []
        for item in candidates:
            item_keywords = set(item.tags) | set(extract_keywords(item.content))
            relevance = len(keywords & item_keywords) * 0.22
            recency = max(0.0, 0.25 - min(days_since(item.timestamp) * 0.02, 0.25))
            kind_bonus = 0.12 if item.kind in {"event", "user", "summary"} else 0.0
            score = (
                item.importance * 0.45
                + item.emotional_weight * 0.15
                + recency
                + relevance
                + kind_bonus
            )
            ranked.append((score, item))

        selected: list[MemoryItem] = []
        seen: set[str] = set()
        for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True):
            key = item.summary or item.content
            if key in seen:
                continue
            seen.add(key)
            selected.append(item)
            if len(selected) >= limit:
                break

        for item in selected:
            item.access_count += 1
            item.last_accessed_at = utc_now_iso()
        self._persist()
        return selected

    @catch_and_log(logger)
    def remember_turn(
        self,
        user_text: str,
        agent_reply: str,
        parsed: Parse,
        emotion_state: EmotionState,
        action_result: str | None = None,
    ) -> None:
        user_item = MemoryItem(
            content=user_text,
            kind="user",
            importance=self._score_importance(parsed, emotion_state, is_user=True),
            emotional_weight=abs(emotion_state.valence - 0.5) + abs(emotion_state.arousal - 0.5),
            tags=extract_keywords(user_text),
            summary=self._build_summary(user_text),
        )
        agent_item = MemoryItem(
            content=agent_reply,
            kind="assistant",
            importance=max(parsed.importance_hint * 0.7, 0.30),
            emotional_weight=0.35,
            tags=extract_keywords(agent_reply),
            summary=self._build_summary(agent_reply),
            source="self",
        )

        self.snapshot.short_term.extend([user_item, agent_item])

        if parsed.intent == "memory_save":
            self._remember_important_event(user_text, parsed, emotion_state)
        if action_result:
            self._remember_action_result(action_result, parsed)

        self.maintain()

    @catch_and_log(logger)
    def maintain(self) -> None:
        self._compress_short_term()
        self._forget_short_term()
        self._forget_long_term()
        self._trim_important_events()
        self._persist()

    def important_event_summaries(self, limit: int = 5) -> list[str]:
        events = sorted(
            self.snapshot.important_events,
            key=lambda item: (item.importance, item.timestamp),
            reverse=True,
        )
        return [f"{item.summary or item.content}" for item in events[:limit]]

    def stats(self) -> dict[str, int]:
        return {
            "short_term": len(self.snapshot.short_term),
            "long_term": len(self.snapshot.long_term),
            "important_events": len(self.snapshot.important_events),
        }

    def _load(self) -> MemorySnapshot:
        if not self.storage_path.exists():
            return MemorySnapshot()
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return MemorySnapshot()
        return MemorySnapshot.from_dict(payload)

    def _persist(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(self.snapshot.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _score_importance(
        self, parsed: Parse, emotion_state: EmotionState, is_user: bool = False
    ) -> float:
        score = parsed.importance_hint
        if parsed.sentiment in {"negative", "urgent"}:
            score += 0.10
        if parsed.asks_memory:
            score += 0.12
        if is_user and parsed.action.action_type != "none":
            score += 0.10
        score += abs(emotion_state.valence - 0.5) * 0.08
        return min(score, 0.98)

    def _remember_important_event(
        self, text: str, parsed: Parse, emotion_state: EmotionState
    ) -> None:
        event = MemoryItem(
            content=text,
            kind="event",
            importance=max(0.88, parsed.importance_hint),
            emotional_weight=abs(emotion_state.valence - 0.5) + 0.4,
            tags=extract_keywords(text),
            summary=self._build_summary(text),
            source="user_marked",
        )
        self.snapshot.important_events.append(event)

    def _remember_action_result(self, action_result: str, parsed: Parse) -> None:
        item = MemoryItem(
            content=action_result,
            kind="reflection",
            importance=max(0.62, parsed.importance_hint),
            emotional_weight=0.45,
            tags=extract_keywords(action_result),
            summary=self._build_summary(action_result),
            source="action_feedback",
        )
        self.snapshot.long_term.append(item)

    def _compress_short_term(self) -> None:
        max_short = self.config.MAX_SHORT_TERM_MEMORIES
        window = self.config.COMPRESSION_WINDOW
        while len(self.snapshot.short_term) > max_short:
            compact_block = self.snapshot.short_term[:window]
            if not compact_block:
                break

            summary = self._summarize_memories(compact_block)
            self.snapshot.long_term.append(summary)
            self.snapshot.short_term = self.snapshot.short_term[window:]
            self.snapshot.last_compacted_at = utc_now_iso()

            for item in compact_block:
                if item.importance >= 0.84 and item.kind == "user":
                    self.snapshot.important_events.append(
                        MemoryItem(
                            content=item.content,
                            kind="event",
                            importance=item.importance,
                            emotional_weight=item.emotional_weight,
                            tags=item.tags,
                            summary=item.summary,
                            source="compaction",
                        )
                    )

    def _forget_short_term(self) -> None:
        expire_hours = self.config.SHORT_TERM_EXPIRE_HOURS
        self.snapshot.short_term = [
            item
            for item in self.snapshot.short_term
            if item.importance >= 0.68 or hours_since(item.timestamp) <= expire_hours
        ]

    def _forget_long_term(self) -> None:
        long_term_days = self.config.LONG_TERM_FORGET_DAYS
        important_days = self.config.IMPORTANT_FORGET_DAYS

        self.snapshot.long_term = [
            item
            for item in self.snapshot.long_term
            if item.importance >= 0.76
            or days_since(item.timestamp) <= long_term_days
            or item.access_count >= 2
        ]
        self.snapshot.important_events = [
            item
            for item in self.snapshot.important_events
            if item.importance >= 0.90
            or days_since(item.timestamp) <= important_days
            or item.access_count >= 1
        ]

        self.snapshot.long_term = sorted(
            self.snapshot.long_term,
            key=lambda item: (item.importance, item.access_count, item.timestamp),
            reverse=True,
        )[: self.config.MAX_LONG_TERM_MEMORIES]

    def _trim_important_events(self) -> None:
        unique: dict[str, MemoryItem] = {}
        for item in self.snapshot.important_events:
            key = item.summary or item.content
            existing = unique.get(key)
            if existing is None or item.importance > existing.importance:
                unique[key] = item
        self.snapshot.important_events = sorted(
            unique.values(),
            key=lambda item: (item.importance, item.timestamp),
            reverse=True,
        )[: self.config.MAX_IMPORTANT_EVENTS]

    def _build_summary(self, text: str, max_length: int = 40) -> str:
        cleaned = " ".join(text.split())
        if len(cleaned) <= max_length:
            return cleaned
        return f"{cleaned[:max_length - 1]}…"

    def _summarize_memories(self, memories: list[MemoryItem]) -> MemoryItem:
        user_points = [item.summary or item.content for item in memories if item.kind == "user"]
        tags: list[str] = []
        for item in memories:
            for tag in item.tags:
                if tag not in tags:
                    tags.append(tag)

        top_points = "；".join(user_points[:3]) if user_points else "一段普通对话"
        summary_text = f"阶段记忆压缩: {top_points}"
        return MemoryItem(
            content=summary_text,
            kind="summary",
            importance=max(item.importance for item in memories) * 0.92,
            emotional_weight=sum(item.emotional_weight for item in memories) / max(len(memories), 1),
            tags=tags[:8],
            summary=summary_text,
            source="auto_compaction",
        )

