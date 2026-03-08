from __future__ import annotations

from soul.modules.actions import ActionResult, ComputerController
from soul.utils.type import ActionRequest, ToolSpec


class ToolRegistry:
    def __init__(self, controller: ComputerController) -> None:
        self.controller = controller

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec("open_app", "Open a local desktop application.", self._schema(["target"])),
            ToolSpec("open_url", "Open a web URL in the browser.", self._schema(["target"])),
            ToolSpec("search_web", "Search the web in the default browser.", self._schema(["target"])),
            ToolSpec("list_processes", "List running processes or applications.", self._schema([])),
            ToolSpec("list_windows", "List visible desktop windows.", self._schema([])),
            ToolSpec("inspect_screen", "Capture and inspect the current desktop screen.", self._schema([])),
            ToolSpec("capture_screen", "Take a screenshot and save it.", self._schema([])),
            ToolSpec("read_file", "Read a text file inside the workspace.", self._schema(["target"])),
            ToolSpec(
                "write_file",
                "Create or overwrite a text file inside the workspace.",
                self._schema(["target"], {"content": {"type": "string"}}),
            ),
            ToolSpec("create_dir", "Create a directory inside the workspace.", self._schema(["target"])),
            ToolSpec("list_dir", "List files in a workspace directory.", self._schema([])),
            ToolSpec("run_command", "Run a shell command if it is safe.", self._schema(["target"])),
            ToolSpec(
                "type_text",
                "Type text into the currently focused window.",
                self._schema(["target"]),
            ),
            ToolSpec(
                "hotkey",
                "Trigger a keyboard shortcut.",
                {
                    "type": "object",
                    "properties": {"keys": {"type": "array", "items": {"type": "string"}}},
                    "required": ["keys"],
                },
            ),
            ToolSpec("focus_window", "Focus a desktop window by title.", self._schema(["target"])),
            ToolSpec(
                "click",
                "Click screen coordinates.",
                {
                    "type": "object",
                    "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
                    "required": ["x", "y"],
                },
            ),
            ToolSpec(
                "scroll",
                "Scroll the mouse wheel.",
                {
                    "type": "object",
                    "properties": {"amount": {"type": "integer"}},
                    "required": ["amount"],
                },
            ),
        ]

    def execute_tool(self, name: str, arguments: dict) -> ActionResult:
        if name == "hotkey":
            action = ActionRequest(
                action_type="hotkey",
                target="+".join(arguments.get("keys", [])),
                parameters={"keys": arguments.get("keys", [])},
                reason="模型选择了快捷键工具",
            )
            return self.controller.execute(action)

        if name == "click":
            action = ActionRequest(
                action_type="click",
                target=f"{arguments.get('x')},{arguments.get('y')}",
                parameters={"x": arguments.get("x"), "y": arguments.get("y")},
                reason="模型选择了点击工具",
            )
            return self.controller.execute(action)

        if name == "scroll":
            action = ActionRequest(
                action_type="scroll",
                target=str(arguments.get("amount", 0)),
                parameters={"amount": arguments.get("amount", 0)},
                reason="模型选择了滚动工具",
            )
            return self.controller.execute(action)

        target = str(arguments.get("target", "") or arguments.get("path", "") or ".")
        parameters = {}
        if "content" in arguments:
            parameters["content"] = arguments["content"]
        if "text" in arguments:
            parameters["text"] = arguments["text"]
        action = ActionRequest(
            action_type=name,  # type: ignore[arg-type]
            target=target,
            parameters=parameters,
            reason="模型选择了工具动作",
        )
        return self.controller.execute(action)

    def _schema(self, required: list[str], extra: dict | None = None) -> dict:
        properties = {"target": {"type": "string"}}
        if extra:
            properties.update(extra)
        return {"type": "object", "properties": properties, "required": required}

