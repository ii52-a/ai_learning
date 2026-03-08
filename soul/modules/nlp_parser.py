from __future__ import annotations

import json
import re
from typing import Any

from soul.utils import util
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import ActionRequest, Entity, Parse, ParseError

logger = Logger(__name__)


class Parser:
    def __init__(self, llm_client: Any = None):
        self.llm_client = llm_client

    @catch_and_log(logger, ParseError())
    def llm_parse(self, text: str) -> Parse:
        if self.llm_client is None:
            return self.local_parse(text)

        parse_raw = self.llm_client.chat([util.LLMContent.get_parse_input_text(text)])
        if parse_raw is None:
            return self.local_parse(text)

        content = parse_raw.content if hasattr(parse_raw, "content") else parse_raw.get("content", "")
        payload = json.loads(content)
        entities = [Entity(type=item["type"], value=item["value"]) for item in payload.get("entities", [])]
        action_payload = payload.get("action", {}) or {}
        return Parse(
            text=text,
            subject=payload.get("subject", ""),
            object=payload.get("object", ""),
            intent=payload.get("intent", "chat"),
            entities=entities,
            sentiment=payload.get("sentiment", "neutral"),
            importance_hint=float(payload.get("importance_hint", 0.4)),
            asks_memory=bool(payload.get("asks_memory", False)),
            action=ActionRequest(
                action_type=action_payload.get("action_type", "none"),
                target=action_payload.get("target", ""),
                parameters=action_payload.get("parameters", {}),
                reason=action_payload.get("reason", ""),
                requires_confirmation=bool(action_payload.get("requires_confirmation", False)),
                confidence=float(action_payload.get("confidence", 0.7)),
            ),
        )

    @staticmethod
    def local_parse(text: str) -> Parse:
        normalized_text = text.strip()
        lowered = normalized_text.lower()
        keywords = util.extract_keywords(text)

        intent = "chat"
        asks_memory = False
        sentiment = Parser._detect_sentiment(lowered)
        importance_hint = Parser._detect_importance(normalized_text)
        action = ActionRequest()
        entities = [Entity(type="keyword", value=word) for word in keywords]

        if any(flag in normalized_text for flag in ["记住", "别忘", "记一下", "帮我记", "请记住"]):
            intent = "memory_save"
            asks_memory = True
            importance_hint = max(importance_hint, 0.82)
        elif any(flag in normalized_text for flag in ["你还记得", "我之前说过", "记不记得", "回忆一下"]):
            intent = "memory_query"
            asks_memory = True
            importance_hint = max(importance_hint, 0.72)
        elif normalized_text in {"/status"} or any(
            flag in normalized_text for flag in ["心跳", "状态", "情绪", "你现在怎么样"]
        ):
            intent = "status_query"
        elif Parser._looks_like_task(normalized_text):
            intent = "task_plan"
        else:
            action = Parser._detect_action(normalized_text)
            if action.action_type != "none":
                intent = f"action_{action.action_type}"

        return Parse(
            text=text,
            subject="user",
            object="agent",
            intent=intent,
            entities=entities,
            sentiment=sentiment,
            importance_hint=importance_hint,
            asks_memory=asks_memory,
            action=action,
        )

    @staticmethod
    def _looks_like_task(text: str) -> bool:
        multi_step_markers = ["然后", "再", "接着", "之后", "并且", "同时", "一步步", "任务"]
        action_markers = ["打开", "输入", "点击", "聚焦", "截图", "滚动", "搜索", "执行", "创建", "写入", "查看", "读取"]
        return any(marker in text for marker in multi_step_markers) and any(marker in text for marker in action_markers)

    @staticmethod
    def _detect_sentiment(text: str) -> str:
        positive = ["开心", "高兴", "喜欢", "棒", "不错", "谢谢", "厉害", "爱"]
        negative = ["难过", "烦", "生气", "讨厌", "崩溃", "糟糕", "痛苦", "失望"]
        urgent = ["立刻", "马上", "赶紧", "紧急", "尽快"]

        if any(word in text for word in urgent):
            return "urgent"
        if any(word in text for word in negative):
            return "negative"
        if any(word in text for word in positive):
            return "positive"
        return "neutral"

    @staticmethod
    def _detect_importance(text: str) -> float:
        score = 0.35
        important_markers = ["生日", "截止", "密码", "偏好", "喜欢", "讨厌", "目标", "计划", "名字", "文件", "程序"]
        if any(word in text for word in important_markers):
            score += 0.28
        if re.search(r"\d{4}[-/年]\d{1,2}", text) or re.search(r"\d{1,2}[:：]\d{2}", text):
            score += 0.18
        if len(text) >= 40:
            score += 0.08
        return min(score, 0.95)

    @staticmethod
    def _detect_action(original_text: str) -> ActionRequest:
        text = original_text.strip()
        lowered = text.lower()

        if lowered in {"/window", "/windows"}:
            return ActionRequest(
                action_type="list_windows",
                target="desktop",
                reason="用户要求查看当前窗口",
                confidence=0.99,
            )
        if lowered == "/screen":
            return ActionRequest(
                action_type="inspect_screen",
                target="desktop",
                reason="用户要求查看当前屏幕",
                confidence=0.99,
            )
        if lowered == "/processes":
            return ActionRequest(
                action_type="list_processes",
                target="system",
                reason="用户要求查看当前进程",
                confidence=0.99,
            )

        write_action = Parser._detect_write_file_action(text)
        if write_action.action_type != "none":
            return write_action

        read_match = re.search(
            r"(?:读取|查看|打开|显示)(?:文件)?\s*([A-Za-z]:\\[^\s]+|\.?[\\/][^\s]+|[^\s，。！？:：]+?\.[A-Za-z0-9一-龥]+)",
            text,
            re.IGNORECASE,
        )
        if read_match and "网页" not in text and "网站" not in text:
            return ActionRequest(
                action_type="read_file",
                target=read_match.group(1).strip(),
                reason="用户要求读取文件",
                confidence=0.93,
            )

        create_dir_match = re.search(
            r"(?:创建|新建)(?:文件夹|目录)\s*([A-Za-z]:\\[^\s]+|\.?[\\/][^\s]+|[^\s，。！？:：]+)",
            text,
            re.IGNORECASE,
        )
        if create_dir_match:
            return ActionRequest(
                action_type="create_dir",
                target=create_dir_match.group(1).strip(),
                reason="用户要求创建目录",
                confidence=0.92,
            )

        list_dir_match = re.search(
            r"(?:列出|查看|显示)(?:目录|文件夹|文件)\s*([A-Za-z]:\\[^\s]+|\.?[\\/][^\s]+)?",
            text,
            re.IGNORECASE,
        )
        if list_dir_match and any(word in text for word in ["目录", "文件夹", "文件列表", "列出文件"]):
            return ActionRequest(
                action_type="list_dir",
                target=(list_dir_match.group(1) or ".").strip(),
                reason="用户要求列出目录内容",
                confidence=0.88,
            )

        if any(flag in text for flag in ["有哪些程序", "查看程序", "运行中的程序", "查看进程", "当前进程"]):
            return ActionRequest(
                action_type="list_processes",
                target="system",
                reason="用户要求查看当前运行的程序或进程",
                confidence=0.92,
            )

        url_match = re.search(r"https?://\S+|www\.\S+", text, re.IGNORECASE)
        if "打开" in text and url_match:
            return ActionRequest(
                action_type="open_url",
                target=url_match.group(0),
                reason="用户要求打开网页",
                confidence=0.96,
            )

        search_match = re.search(r"(?:搜索|查一下|帮我搜)\s*(.+)", text)
        if search_match:
            return ActionRequest(
                action_type="search_web",
                target=search_match.group(1).strip(),
                reason="用户要求在网页里搜索内容",
                confidence=0.90,
            )

        if any(flag in text for flag in ["截图", "截屏", "看看屏幕", "看一下屏幕", "观察屏幕"]):
            return ActionRequest(
                action_type="inspect_screen" if ("看" in text or "观察" in text) else "capture_screen",
                target="desktop",
                reason="用户要求查看当前屏幕",
                confidence=0.92,
            )

        if any(flag in text for flag in ["列出窗口", "有哪些窗口", "窗口列表"]):
            return ActionRequest(
                action_type="list_windows",
                target="desktop",
                reason="用户要求列出可见窗口",
                confidence=0.90,
            )

        focus_match = re.search(r"(?:聚焦|切换到|激活窗口)\s*([^\n，。！？.!?]+)", text)
        if focus_match:
            return ActionRequest(
                action_type="focus_window",
                target=focus_match.group(1).strip(),
                reason="用户要求切换到目标窗口",
                confidence=0.88,
            )

        click_match = re.search(r"点击\s*(\d+)\s*[,，xX]\s*(\d+)", text)
        if click_match:
            return ActionRequest(
                action_type="click",
                target=f"{click_match.group(1)},{click_match.group(2)}",
                parameters={"x": int(click_match.group(1)), "y": int(click_match.group(2))},
                reason="用户提供了明确点击坐标",
                confidence=0.93,
            )

        scroll_match = re.search(r"滚动\s*(-?\d+)", text)
        if scroll_match:
            return ActionRequest(
                action_type="scroll",
                target=scroll_match.group(1),
                parameters={"amount": int(scroll_match.group(1))},
                reason="用户要求滚动",
                confidence=0.90,
            )

        run_command_match = re.search(r"(?:执行|运行)命令[:：]?\s*(.+)", text)
        if run_command_match:
            return ActionRequest(
                action_type="run_command",
                target=run_command_match.group(1).strip(),
                reason="用户要求执行命令",
                requires_confirmation=True,
                confidence=0.95,
            )

        type_text_match = re.search(r"(?:输入|打字)[:：]?\s*(.+)", text)
        if type_text_match:
            typed_text = type_text_match.group(1).strip()
            return ActionRequest(
                action_type="type_text",
                target=typed_text,
                parameters={"text": typed_text},
                reason="用户要求输入文本",
                confidence=0.91,
            )

        hotkey_match = re.search(r"(?:按下|触发)快捷键[:：]?\s*([A-Za-z0-9+ ]+)", text)
        if hotkey_match:
            keys = [key.strip().lower() for key in hotkey_match.group(1).split("+") if key.strip()]
            return ActionRequest(
                action_type="hotkey",
                target="+".join(keys),
                parameters={"keys": keys},
                reason="用户要求触发快捷键",
                confidence=0.90,
            )

        open_app_match = re.search(r"打开\s*([^\n]+)", text)
        if open_app_match and "网页" not in text and "网站" not in text:
            return ActionRequest(
                action_type="open_app",
                target=open_app_match.group(1).strip("。！？!? "),
                reason="用户要求打开应用",
                confidence=0.88,
            )

        return ActionRequest()

    @staticmethod
    def _detect_write_file_action(text: str) -> ActionRequest:
        if not any(flag in text for flag in ["创建", "新建", "生成", "写入"]):
            return ActionRequest()

        content = ""
        content_match = re.search(r"(?:内容为|写入|内容是|内容:|内容：)\s*(.+)$", text, re.IGNORECASE)
        if content_match:
            content = content_match.group(1).strip().strip('"').strip("'")
            text = text[: content_match.start()].strip()

        target = Parser._extract_file_target(text)
        if not target:
            return ActionRequest()

        return ActionRequest(
            action_type="write_file",
            target=target,
            parameters={"content": content},
            reason="用户要求创建或写入文件",
            confidence=0.95,
        )

    @staticmethod
    def _extract_file_target(text: str) -> str:
        sentence_match = re.search(
            r"(?:请|帮我|麻烦你)?\s*(?:在)?\s*(桌面|desktop)?(?:上)?\s*(?:创建|新建|生成|写入)?(?:一个|一份|个)?\s*([^\s，。！？:：\\/]+?\.[A-Za-z0-9一-龥]+)$",
            text,
            re.IGNORECASE,
        )
        if sentence_match:
            base = sentence_match.group(1)
            filename = Parser._normalize_file_target(sentence_match.group(2))
            if base:
                return f"{base}\\{filename}"
            return filename

        quoted_match = re.search(r"[\"“](.+?\.[A-Za-z0-9一-龥]+)[\"”]", text)
        if quoted_match:
            return Parser._normalize_file_target(quoted_match.group(1))

        path_match = re.search(r"([A-Za-z]:\\[^\s]+|\.?[\\/][^\s]+|(?:桌面|desktop)[\\/][^\s]+)", text, re.IGNORECASE)
        if path_match and "." in path_match.group(1):
            return Parser._normalize_file_target(path_match.group(1))

        file_match = re.search(r"([^\s，。！？:：]*?\.[A-Za-z0-9一-龥]+)", text)
        if file_match:
            return Parser._normalize_file_target(file_match.group(1))

        return ""

    @staticmethod
    def _normalize_file_target(target: str) -> str:
        cleaned = target.strip().strip("。 ，,;；\"'“”")
        cleaned = re.sub(r"^(创建|新建|生成|写入)", "", cleaned)
        cleaned = re.sub(r"^(一个|一份|一张|一个名为)", "", cleaned)
        cleaned = cleaned.strip()

        if cleaned.startswith("你的自我介绍"):
            cleaned = "多伦娜的自我介绍.txt"

        if cleaned.startswith("桌面") and "." in cleaned:
            return cleaned
        return cleaned
