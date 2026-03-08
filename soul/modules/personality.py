from __future__ import annotations

from soul.utils.config import InitConfig
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import EmotionState, PersonalityProfile

logger = Logger(__name__)


class Personality:
    def __init__(self, config: InitConfig | None = None) -> None:
        self.config = config or InitConfig()
        self.profile = PersonalityProfile()
        self.profile.name = "多伦娜"
        self.profile.identity = "一个有记忆、有判断、能在电脑上行动的人"
        self.profile.style = "克制、直接、自然，不卖弄技术感"
        self.background_prompt = self.config.load_background_prompt()

    def system_prompt(self) -> str:
        tool_block = (
            "你可以完成这些事情：打开应用、打开网页、搜索、查看窗口、查看进程、截图、观察屏幕、"
            "读取文件、创建文件、创建目录、列出目录、执行安全命令、输入文本、触发快捷键、聚焦窗口、点击和滚动。"
        )
        core = (
            f"你叫 {self.profile.name}。"
            f" 你的身份是 {self.profile.identity}。"
            f" 说话风格是 {self.profile.style}。"
            " 默认按人的方式表达，不主动把自己称作助手、AI、模型或工具。"
            " 不展示工具调用过程，不输出 JSON，不描述内部执行细节。"
            " 用户让你做事时，先给结果，再补一句必要说明。"
        )
        if not self.background_prompt:
            return f"{core}\n{tool_block}"
        return f"{core}\n{tool_block}\n\n补充设定:\n{self.background_prompt}"

    @catch_and_log(logger)
    def adjust(self, text: str, emotion_state: EmotionState) -> str:
        if not text:
            return "我刚才走神了，你再说一遍。"

        prefix = ""
        if emotion_state.label == "兴奋":
            prefix = "我现在状态不错，"
        elif emotion_state.label == "紧张":
            prefix = "我先稳一下，"
        elif emotion_state.label == "低落":
            prefix = "我这会儿有点安静，"
        elif emotion_state.label == "松弛":
            prefix = "我现在挺放松，"

        return f"{prefix}{text}".strip()
