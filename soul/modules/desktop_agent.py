from __future__ import annotations

from soul.modules.perception import DesktopPerception
from soul.modules.tool_registry import ToolRegistry
from soul.utils.type import ModelResponse
from soul.utils.util import LLMContent


class DesktopAutopilot:
    def __init__(self, model_manager, perception: DesktopPerception, tools: ToolRegistry, max_rounds: int = 5):
        self.model_manager = model_manager
        self.perception = perception
        self.tools = tools
        self.max_rounds = max_rounds

    def run(self, goal: str) -> str:
        if not self.model_manager.available_aliases():
            return "当前没有可用模型，无法启动桌面自动执行。"

        history: list[str] = []
        for _ in range(self.max_rounds):
            snapshot = self.perception.inspect()
            prompt = self._build_prompt(goal, snapshot, history)
            response = self.model_manager.chat(
                [LLMContent.user_message_standard(prompt)],
                temperature=0.2,
                max_tokens=500,
                tools=self.tools.specs(),
            )
            if response is None:
                return self._final_from_history(history, "模型没有返回结果。")

            if response.tool_calls:
                for call in response.tool_calls:
                    result = self.tools.execute_tool(call.name, call.arguments)
                    history.append(f"{call.name}: {result.message}")
                continue

            final_text = response.content.strip()
            if final_text:
                return self._final_from_history(history, final_text)

        return self._final_from_history(history, "已达到最大桌面执行轮数。")

    def _build_prompt(self, goal, snapshot, history) -> str:
        feedback = "\n".join(f"- {item}" for item in history) or "- 暂无动作"
        windows = " | ".join(snapshot.visible_windows[:8]) or "无"
        return (
            "你是一个桌面自动执行代理。\n"
            "优先根据当前桌面状态选择下一步工具，直到任务完成再直接回复。\n"
            f"目标: {goal}\n"
            f"活动窗口: {snapshot.active_window or '未知'}\n"
            f"可见窗口: {windows}\n"
            f"OCR: {snapshot.ocr_excerpt or '无'}\n"
            f"截图路径: {snapshot.screenshot_path or '无'}\n"
            f"已执行历史:\n{feedback}\n"
            "如果还需要动作，请调用工具；如果任务已经完成，请直接自然语言总结。"
        )

    def _final_from_history(self, history: list[str], message: str) -> str:
        if not history:
            return message
        return f"{message}\n执行历史:\n" + "\n".join(f"- {item}" for item in history)

