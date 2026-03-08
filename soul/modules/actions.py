from __future__ import annotations

import os
import re
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from soul.modules.perception import DesktopPerception
from soul.utils.config import BASE_DIR, InitConfig
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import ActionRequest, ScreenSnapshot

logger = Logger(__name__)


@dataclass
class ActionResult:
    success: bool
    message: str
    payload: dict | None = None


class ComputerController:
    APP_ALIASES = {
        "记事本": "notepad.exe",
        "notepad": "notepad.exe",
        "画图": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "计算器": "calc.exe",
        "calc": "calc.exe",
        "资源管理器": "explorer.exe",
        "文件资源管理器": "explorer.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "命令提示符": "cmd.exe",
        "powershell": "powershell.exe",
        "浏览器": "msedge.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "qq": "qq",
        "腾讯qq": "qq",
        "qq软件": "qq",
        "微信": "wechat",
        "wechat": "wechat",
        "vscode": "code",
        "visual studio code": "code",
        "chrome": "chrome.exe",
        "谷歌浏览器": "chrome.exe",
    }

    BLOCKED_COMMANDS = {
        "rm",
        "rmdir",
        "del ",
        "format",
        "shutdown",
        "restart",
        "taskkill",
        "reg delete",
        "sc delete",
        "cipher /w",
    }

    def __init__(
        self,
        config: InitConfig | None = None,
        perception: DesktopPerception | None = None,
    ) -> None:
        self.config = config or InitConfig()
        self.perception = perception or DesktopPerception(config=self.config)
        self.root_dir = BASE_DIR.resolve()
        self.user_home = Path.home().resolve()
        self.allowed_external_dirs = {
            "desktop": (self.user_home / "Desktop").resolve(),
            "documents": (self.user_home / "Documents").resolve(),
            "downloads": (self.user_home / "Downloads").resolve(),
        }

    def describe_capabilities(self) -> str:
        return (
            "支持打开应用、打开本地文件、打开网页、网页搜索、查看窗口、查看进程、截图、观察屏幕、"
            "读取文件、创建文件、创建目录、列出目录、执行安全命令、输入文本、快捷键、聚焦窗口、点击和滚动。"
        )

    @catch_and_log(logger, ActionResult(False, "执行动作时发生异常。"))
    def execute(self, action: ActionRequest) -> ActionResult:
        if not self.config.COMPUTER_CONTROL_ENABLED:
            return ActionResult(False, "电脑控制功能已关闭。")

        handlers = {
            "none": self._noop,
            "open_url": lambda: self._open_url(action.target),
            "search_web": lambda: self._search_web(action.target),
            "open_app": lambda: self._open_app(action.target),
            "run_command": lambda: self._run_command(action.target),
            "type_text": lambda: self._type_text(action.parameters.get("text", action.target)),
            "hotkey": lambda: self._press_hotkey(action.parameters.get("keys", [])),
            "capture_screen": self._capture_screen,
            "inspect_screen": self._inspect_screen,
            "list_windows": self._list_windows,
            "focus_window": lambda: self._focus_window(action.target),
            "list_processes": self._list_processes,
            "list_dir": lambda: self._list_dir(action.target or "."),
            "read_file": lambda: self._read_file(action.target),
            "write_file": lambda: self._write_file(action.target, action.parameters.get("content", "")),
            "create_dir": lambda: self._create_dir(action.target),
            "click": lambda: self._click(action.parameters.get("x"), action.parameters.get("y")),
            "scroll": lambda: self._scroll(action.parameters.get("amount", 0)),
        }
        handler = handlers.get(action.action_type)
        if handler is None:
            return ActionResult(False, f"未知动作类型: {action.action_type}")
        return handler()

    def _noop(self) -> ActionResult:
        return ActionResult(True, "这次没有需要执行的动作。")

    def _open_url(self, url: str) -> ActionResult:
        target = url if url.startswith(("http://", "https://")) else f"https://{url}"
        if webbrowser.open(target):
            return ActionResult(True, f"网页已经打开了。", {"url": target})
        return ActionResult(False, f"网页没有成功打开。", {"url": target})

    def _search_web(self, query: str) -> ActionResult:
        target = f"https://www.google.com/search?q={query}"
        if webbrowser.open(target):
            return ActionResult(True, f"我已经打开搜索结果了。", {"query": query, "url": target})
        return ActionResult(False, f"搜索页没有成功打开。", {"query": query, "url": target})

    def _open_app(self, app_name: str) -> ActionResult:
        raw_name = (app_name or "").strip().strip("。！？?!.，,")
        file_result = self._open_local_file_if_exists(raw_name)
        if file_result is not None:
            return file_result
        cleaned_name = self._normalize_app_name(raw_name)

        direct_target = self._resolve_direct_app_target(cleaned_name)
        if direct_target is not None:
            started = self._start_target(direct_target)
            if started:
                return ActionResult(
                    True,
                    f"{self._display_name(cleaned_name)}已经打开了。",
                    {"target": str(direct_target), "query": cleaned_name},
                )

        discovered = self._discover_app_targets(cleaned_name)
        for target in discovered:
            if self._start_target(target):
                return ActionResult(
                    True,
                    f"{self._display_name(cleaned_name)}已经打开了。",
                    {"target": str(target), "query": cleaned_name},
                )

        suggestions = self._format_suggestions(discovered)
        base_message = f"我没能直接打开{self._display_name(cleaned_name)}。"
        if suggestions:
            return ActionResult(False, f"{base_message} 我找到了这些可能的入口：{suggestions}", {"matches": [str(item) for item in discovered[:5]]})
        return ActionResult(False, f"{base_message} 系统里暂时没找到明显匹配的入口。", {"query": cleaned_name})

    def _run_command(self, command: str) -> ActionResult:
        lowered = command.lower()
        if any(blocked in lowered for blocked in self.BLOCKED_COMMANDS):
            return ActionResult(False, f"这个命令被安全策略拦住了。")

        try:
            subprocess.Popen(command, shell=True, cwd=str(self.root_dir))
        except OSError as exc:
            return ActionResult(False, f"命令执行失败：{exc}")
        return ActionResult(True, "命令已经执行了。")

    def _type_text(self, text: str) -> ActionResult:
        pyautogui = self._load_pyautogui()
        if pyautogui is None:
            return ActionResult(False, "缺少 pyautogui，暂时没法自动输入。")
        pyautogui.write(text, interval=0.02)
        return ActionResult(True, "文字已经输入好了。")

    def _press_hotkey(self, keys: list[str]) -> ActionResult:
        pyautogui = self._load_pyautogui()
        if pyautogui is None:
            return ActionResult(False, "缺少 pyautogui，暂时没法触发快捷键。")
        if not keys:
            return ActionResult(False, "没有可执行的快捷键。")
        pyautogui.hotkey(*keys)
        return ActionResult(True, f"快捷键 {'+'.join(keys)} 已经触发。")

    def _capture_screen(self) -> ActionResult:
        screenshot_path = self.perception.capture_screen()
        if screenshot_path is None:
            return ActionResult(False, "截图失败了，缺少可用依赖。")
        return ActionResult(True, "截图已经保存好了。", {"screenshot_path": str(screenshot_path)})

    def _inspect_screen(self) -> ActionResult:
        snapshot = self.perception.inspect()
        if not snapshot.captured_at:
            return ActionResult(False, "这次没看清屏幕。")
        return ActionResult(True, self._snapshot_message(snapshot), {"snapshot": snapshot.__dict__})

    def _list_windows(self) -> ActionResult:
        windows = self.perception.list_windows()
        if not windows:
            return ActionResult(False, "当前没有枚举到可见窗口。")
        return ActionResult(True, "当前可见窗口有: " + " | ".join(windows[:10]), {"windows": windows})

    def _focus_window(self, title: str) -> ActionResult:
        if self.perception.focus_window(title):
            return ActionResult(True, f"我已经尝试切到《{title}》。")
        return ActionResult(False, f"没能切到《{title}》，可能是窗口名不匹配。")

    def _list_processes(self) -> ActionResult:
        try:
            completed = subprocess.run(
                ["tasklist", "/fo", "csv", "/nh"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                check=True,
            )
            lines = [line.strip().strip('"') for line in completed.stdout.splitlines() if line.strip()]
            names: list[str] = []
            for line in lines[:20]:
                parts = [part.strip('"') for part in line.split('","')]
                if parts:
                    names.append(parts[0])
            return ActionResult(True, "运行中的程序有: " + " | ".join(names[:12]), {"processes": names})
        except (OSError, subprocess.SubprocessError):
            return ActionResult(False, "读取进程列表失败了。")

    def _list_dir(self, path_text: str) -> ActionResult:
        try:
            path = self._resolve_workspace_path(path_text, must_exist=True)
        except ValueError as exc:
            return ActionResult(False, str(exc))

        if not path.is_dir():
            return ActionResult(False, f"{path} 不是目录。")
        entries = sorted(item.name for item in path.iterdir())
        preview = " | ".join(entries[:20]) if entries else "(空目录)"
        return ActionResult(True, f"{path} 里有这些内容: {preview}", {"entries": entries, "path": str(path)})

    def _read_file(self, path_text: str) -> ActionResult:
        try:
            path = self._resolve_workspace_path(path_text, must_exist=True)
        except ValueError as exc:
            return ActionResult(False, str(exc))

        if not path.is_file():
            return ActionResult(False, f"{path} 不是文件。")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return ActionResult(False, f"读取文件失败：{exc}")

        preview = content[:500]
        return ActionResult(True, f"我已经读过这个文件了：{path}\n{preview}", {"path": str(path), "content": content})

    def _write_file(self, path_text: str, content: str) -> ActionResult:
        try:
            path = self._resolve_workspace_path(path_text)
        except ValueError as exc:
            return ActionResult(False, str(exc))

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ActionResult(False, f"写入文件失败：{exc}")

        return ActionResult(True, f"文件已经写好了，位置在 {path}。", {"path": str(path), "content": content})

    def _create_dir(self, path_text: str) -> ActionResult:
        try:
            path = self._resolve_workspace_path(path_text)
        except ValueError as exc:
            return ActionResult(False, str(exc))

        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return ActionResult(False, f"创建目录失败：{exc}")

        return ActionResult(True, f"目录已经建好了：{path}。", {"path": str(path)})

    def _click(self, x: int | None, y: int | None) -> ActionResult:
        pyautogui = self._load_pyautogui()
        if pyautogui is None:
            return ActionResult(False, "缺少 pyautogui，暂时没法点击。")
        if x is None or y is None:
            return ActionResult(False, "点击缺少坐标。")
        pyautogui.click(x=int(x), y=int(y))
        return ActionResult(True, f"我已经点了 ({x}, {y})。")

    def _scroll(self, amount: int) -> ActionResult:
        pyautogui = self._load_pyautogui()
        if pyautogui is None:
            return ActionResult(False, "缺少 pyautogui，暂时没法滚动。")
        pyautogui.scroll(int(amount))
        return ActionResult(True, f"我已经滚动了 {amount}。")

    def _snapshot_message(self, snapshot: ScreenSnapshot) -> str:
        windows_preview = " | ".join(snapshot.visible_windows[:5]) if snapshot.visible_windows else "无"
        ocr = snapshot.ocr_excerpt or "未提取到文本"
        return (
            f"我看了一眼屏幕。活动窗口是《{snapshot.active_window or '未知'}》，"
            f"分辨率 {snapshot.screen_size[0]}x{snapshot.screen_size[1]}，"
            f"可见窗口有: {windows_preview}。OCR 摘要: {ocr}"
        )

    def _normalize_app_name(self, app_name: str) -> str:
        cleaned = (app_name or "").strip().strip("。！？?!.，,")
        if "." in cleaned:
            return cleaned.lower()
        cleaned = re.sub(r"(可以吗|行吗|好吗|能吗|一下|一下子)$", "", cleaned)
        cleaned = re.sub(r"(软件|程序|应用)$", "", cleaned)
        cleaned = re.sub(r"(浏览器)$", "", cleaned)
        cleaned = cleaned.strip().lower()
        return self.APP_ALIASES.get(cleaned, cleaned)

    def _resolve_direct_app_target(self, app_name: str) -> str | Path | None:
        alias_target = self.APP_ALIASES.get(app_name, app_name)
        if alias_target.endswith((".exe", ".bat", ".cmd", ".lnk")):
            resolved = shutil.which(alias_target) or alias_target
            return resolved
        if re.search(r"[\\/]|^[A-Za-z]:\\", alias_target):
            return alias_target
        if app_name in {"qq", "wechat", "code"}:
            direct = shutil.which(app_name)
            if direct:
                return direct
        return None

    def _open_local_file_if_exists(self, text: str) -> ActionResult | None:
        candidate_names = [text]
        if "." not in text:
            candidate_names.extend([f"{text}.txt", f"{text}.md", f"{text}.lnk"])

        search_roots = [self.root_dir, *self.allowed_external_dirs.values()]
        for root in search_roots:
            for name in candidate_names:
                candidate = root / name
                if candidate.exists():
                    if self._start_target(candidate):
                        return ActionResult(True, f"《{candidate.name}》已经打开了。", {"target": str(candidate)})
        return None

    def _discover_app_targets(self, app_name: str) -> list[Path]:
        tokens = [token for token in re.split(r"[\s_\-]+", app_name) if token]
        if not tokens:
            return []

        search_roots = [
            self.allowed_external_dirs["desktop"],
            self.user_home / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            self.user_home / "AppData" / "Local" / "Tencent",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
        ]

        matches: list[Path] = []
        seen: set[str] = set()
        for root in search_roots:
            for candidate in self._iter_candidate_files(root):
                name = candidate.stem.lower()
                if all(token in name for token in tokens) or any(token == name for token in tokens):
                    key = str(candidate).lower()
                    if key not in seen:
                        seen.add(key)
                        matches.append(candidate)
                if len(matches) >= 12:
                    return matches
        return matches

    def _iter_candidate_files(self, root: Path, max_depth: int = 4) -> Iterable[Path]:
        if not root.exists():
            return []
        results: list[Path] = []
        root_depth = len(root.parts)
        for current_root, dirnames, filenames in os.walk(root):
            current_path = Path(current_root)
            depth = len(current_path.parts) - root_depth
            if depth >= max_depth:
                dirnames[:] = []
            for filename in filenames:
                lower = filename.lower()
                if lower.endswith((".lnk", ".exe")):
                    results.append(current_path / filename)
        return results

    def _format_suggestions(self, candidates: list[Path]) -> str:
        names = []
        for item in candidates[:5]:
            label = item.stem if item.suffix.lower() == ".lnk" else item.name
            if label not in names:
                names.append(label)
        return "；".join(names)

    def _display_name(self, name: str) -> str:
        if name == "msedge.exe":
            return "Edge"
        if name == "qq":
            return "QQ"
        if name == "wechat":
            return "微信"
        return name

    def _start_target(self, target: str | Path) -> bool:
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.Popen([str(target)], shell=False)
            return True
        except OSError:
            return False

    def _resolve_workspace_path(self, path_text: str, must_exist: bool = False) -> Path:
        raw = (path_text or ".").strip().strip('"').strip("'")
        candidate = self._resolve_special_user_path(raw)
        if candidate is None:
            candidate = Path(raw)

        if not candidate.is_absolute():
            candidate = (self.root_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not self._is_allowed_path(candidate):
            raise ValueError(f"出于安全考虑，只允许访问工作区或常用用户目录: {candidate}")

        if must_exist and not candidate.exists():
            raise ValueError(f"路径不存在: {candidate}")
        return candidate

    def _resolve_special_user_path(self, raw: str) -> Path | None:
        normalized = raw.replace("/", "\\").strip()
        compact = re.sub(r"\s+", "", normalized.lower())
        aliases = {
            "桌面": self.allowed_external_dirs["desktop"],
            "desktop": self.allowed_external_dirs["desktop"],
            "文档": self.allowed_external_dirs["documents"],
            "documents": self.allowed_external_dirs["documents"],
            "下载": self.allowed_external_dirs["downloads"],
            "downloads": self.allowed_external_dirs["downloads"],
        }
        for prefix, base_dir in aliases.items():
            if compact == prefix:
                return base_dir
            if compact.startswith(prefix + "\\") or compact.startswith(prefix + "/"):
                suffix = normalized[len(prefix) :].lstrip("\\/")
                return base_dir / suffix
        return None

    def _is_allowed_path(self, candidate: Path) -> bool:
        try:
            candidate.relative_to(self.root_dir)
            return True
        except ValueError:
            pass

        for allowed_dir in self.allowed_external_dirs.values():
            try:
                candidate.relative_to(allowed_dir)
                return True
            except ValueError:
                continue
        return False

    def _load_pyautogui(self) -> Optional[object]:
        try:
            import pyautogui  # type: ignore
        except ImportError:
            return None
        return pyautogui
