from __future__ import annotations

import re
from datetime import datetime, timezone

from soul.utils.type import Parse


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value)


def hours_since(value: str | None) -> float:
    delta = datetime.now(timezone.utc) - parse_datetime(value)
    return delta.total_seconds() / 3600


def days_since(value: str | None) -> float:
    delta = datetime.now(timezone.utc) - parse_datetime(value)
    return delta.total_seconds() / 86400


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def extract_keywords(text: str) -> list[str]:
    raw_words = re.findall(r"[A-Za-z0-9_./:\\-]+|[\u4e00-\u9fff]{2,}", text.lower())
    stop_words = {
        "一下",
        "这个",
        "那个",
        "你们",
        "我们",
        "他们",
        "然后",
        "现在",
        "今天",
        "刚才",
        "就是",
        "可以",
        "帮我",
        "一下子",
    }
    ordered: list[str] = []
    for word in raw_words:
        if word in stop_words:
            continue
        if word not in ordered:
            ordered.append(word)
    return ordered[:12]


class LLMContent:
    @staticmethod
    def sys_message_standard(content: object) -> dict[str, str]:
        return {"role": "system", "content": str(content)}

    @staticmethod
    def user_message_standard(text: str) -> dict[str, str]:
        return {"role": "user", "content": text}

    @classmethod
    def sys_user_message_standard(cls, parse: Parse, text2: str) -> list[dict[str, str]]:
        return [cls.sys_message_standard(parse), cls.user_message_standard(text2)]

    @classmethod
    def get_parse_input_text(cls, text: str) -> dict[str, str]:
        prompt = f"""
你是一个语义解析模块。
把用户输入解析成 JSON，不要解释，不要输出 Markdown。

当前系统支持的动作类型:
- open_app: 打开应用
- open_url: 打开网页
- search_web: 在浏览器搜索
- list_processes: 查看正在运行的程序/进程
- list_windows: 查看窗口
- inspect_screen: 观察当前屏幕
- capture_screen: 截图
- read_file: 读取文件
- write_file: 创建或覆盖文件
- create_dir: 创建目录
- list_dir: 列出目录内容
- run_command: 执行命令
- type_text: 自动输入文本
- hotkey: 触发快捷键
- focus_window: 聚焦窗口
- click: 坐标点击
- scroll: 滚动

输出字段:
{{
  "intent": string,
  "object": string,
  "subject": string,
  "sentiment": string,
  "importance_hint": number,
  "asks_memory": boolean,
  "entities": [{{"type": string, "value": string}}],
  "action": {{
    "action_type": string,
    "target": string,
    "parameters": object,
    "reason": string,
    "requires_confirmation": boolean,
    "confidence": number
  }}
}}

用户输入:
{text}
"""
        return cls.user_message_standard(prompt.strip())

