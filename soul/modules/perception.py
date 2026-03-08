from __future__ import annotations

import ctypes
import unicodedata
from ctypes import wintypes
from pathlib import Path
from typing import Optional

from soul.utils.config import InitConfig, SCREENSHOT_DIR
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import ScreenSnapshot
from soul.utils.util import utc_now_iso

logger = Logger(__name__)


class DesktopPerception:
    def __init__(self, config: InitConfig | None = None) -> None:
        self.config = config or InitConfig()
        self.config.ensure_runtime()
        self._user32 = ctypes.windll.user32

    def describe_capabilities(self) -> str:
        return "支持截图、读取活动窗口、枚举窗口标题，以及可选 OCR。"

    @catch_and_log(logger, ScreenSnapshot(captured_at=""))
    def inspect(self) -> ScreenSnapshot:
        screenshot_path = self.capture_screen()
        windows = self.list_windows()
        return ScreenSnapshot(
            captured_at=utc_now_iso(),
            screenshot_path=str(screenshot_path) if screenshot_path else "",
            screen_size=self.screen_size(),
            active_window=self._sanitize_text(self.active_window_title()),
            visible_windows=[self._sanitize_text(item) for item in windows],
            ocr_excerpt=self._sanitize_text(self._ocr_from_image(screenshot_path)) if screenshot_path else "",
        )

    @catch_and_log(logger, None)
    def capture_screen(self) -> Optional[Path]:
        screenshot = self._take_screenshot()
        if screenshot is None:
            return None
        filename = SCREENSHOT_DIR / f"screen_{utc_now_iso().replace(':', '-').replace('.', '-')}.png"
        screenshot.save(filename)
        return filename

    def screen_size(self) -> tuple[int, int]:
        width = int(self._user32.GetSystemMetrics(0))
        height = int(self._user32.GetSystemMetrics(1))
        return width, height

    def active_window_title(self) -> str:
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = self._user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buffer, length + 1)
        return self._sanitize_text(buffer.value.strip())

    @catch_and_log(logger, [])
    def list_windows(self) -> list[str]:
        titles: list[str] = []
        enum_windows = self._user32.EnumWindows
        enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def foreach_window(hwnd, l_param):
            if self._user32.IsWindowVisible(hwnd):
                length = self._user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    self._user32.GetWindowTextW(hwnd, buffer, length + 1)
                    title = self._sanitize_text(buffer.value.strip())
                    if title and title not in titles:
                        titles.append(title)
            return True

        enum_windows(enum_windows_proc(foreach_window), 0)
        return titles[:30]

    @catch_and_log(logger, False)
    def focus_window(self, title: str) -> bool:
        try:
            import pygetwindow as gw  # type: ignore
        except ImportError:
            return False

        matches = [win for win in gw.getAllWindows() if title.lower() in win.title.lower()]
        if not matches:
            return False
        matches[0].activate()
        return True

    def _take_screenshot(self):
        try:
            from PIL import ImageGrab  # type: ignore

            return ImageGrab.grab()
        except Exception:
            pass

        try:
            import pyautogui  # type: ignore

            return pyautogui.screenshot()
        except Exception:
            return None

    def _ocr_from_image(self, image_path: Path | None) -> str:
        if image_path is None:
            return ""
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError:
            return ""

        try:
            text = pytesseract.image_to_string(Image.open(image_path), lang="chi_sim+eng")
        except Exception:
            return ""
        return " ".join(text.split())[:240]

    def _sanitize_text(self, text: str) -> str:
        cleaned = []
        for char in text:
            category = unicodedata.category(char)
            if char in {"\u200b", "\ufeff"}:
                continue
            if category.startswith("C") and char not in {"\n", "\r", "\t"}:
                continue
            cleaned.append(char)
        return "".join(cleaned)

