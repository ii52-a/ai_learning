from __future__ import annotations

from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import EmotionState, HeartbeatSnapshot, MemoryItem, Parse, PersonalityProfile

logger = Logger(__name__)


class Responder:
    @staticmethod
    @catch_and_log(logger, "我这会儿没组织好回答。")
    def respond(
        parsed: Parse,
        memories: list[MemoryItem],
        emotion: EmotionState,
        personality: PersonalityProfile,
        heartbeat: HeartbeatSnapshot,
        action_result: str | None = None,
        llm_reply: str | None = None,
        task_result: str | None = None,
    ) -> str:
        if llm_reply:
            return llm_reply

        if parsed.intent == "memory_query":
            filtered = [
                item
                for item in memories
                if item.kind in {"event", "summary", "user"} and (item.summary or item.content) != parsed.text
            ]
            if not filtered:
                return "我暂时没翻到明确相关的记忆。"
            recalled = "；".join(item.summary or item.content for item in filtered[:3])
            return f"我想起来这些：{recalled}"

        if parsed.intent == "memory_save":
            return "这件事我记下了。"

        if parsed.intent == "status_query":
            return f"我现在是{emotion.label}，心跳约 {heartbeat.bpm} BPM，已经运行 {heartbeat.uptime_seconds:.0f} 秒。"

        if parsed.intent == "task_plan" and task_result:
            return task_result

        if action_result:
            return action_result

        if memories:
            remembered = memories[0].summary or memories[0].content
            return f"我在听。关于“{parsed.text}”，我联想到一段相关记忆：{remembered}"

        return f"我知道了。关于“{parsed.text}”，我已经放进当前语境里了。"
