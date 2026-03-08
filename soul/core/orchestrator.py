from __future__ import annotations

import json
import re
import uuid

import dotenv

from soul.llm import ModelManager, build_model_manager
from soul.modules.actions import ComputerController
from soul.modules.desktop_agent import DesktopAutopilot
from soul.modules.emotion import Emotion
from soul.modules.heartbeat import Heartbeat
from soul.modules.memory import Memory
from soul.modules.nlp_parser import Parser
from soul.modules.perception import DesktopPerception
from soul.modules.personality import Personality
from soul.modules.responder import Responder
from soul.modules.tasks import TaskPlanner
from soul.modules.tool_registry import ToolRegistry
from soul.utils.config import InitConfig
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import ActionRequest, Parse, ParseError, TaskPlan
from soul.utils.util import LLMContent

logger = Logger(__name__)
dotenv.load_dotenv()


class SoulCore:
    def __init__(
        self,
        model_manager: ModelManager | None = None,
        parser: Parser | None = None,
        emotion: Emotion | None = None,
        memory: Memory | None = None,
        personality: Personality | None = None,
        responder: Responder | None = None,
        controller: ComputerController | None = None,
        perception: DesktopPerception | None = None,
        task_planner: TaskPlanner | None = None,
        config: InitConfig | None = None,
    ) -> None:
        self.config = config or InitConfig()
        self.config.ensure_runtime()

        self.model_manager = model_manager or build_model_manager(self.config)
        self.perception = perception or DesktopPerception(config=self.config)
        self.parser = parser or Parser(llm_client=self.model_manager)
        self.emotion = emotion or Emotion()
        self.memory = memory or Memory(config=self.config)
        self.personality = personality or Personality(config=self.config)
        self.responder = responder or Responder()
        self.controller = controller or ComputerController(config=self.config, perception=self.perception)
        self.task_planner = task_planner or TaskPlanner(parser=self.parser, config=self.config)
        self.tools = ToolRegistry(self.controller)
        self.desktop_autopilot = DesktopAutopilot(
            model_manager=self.model_manager,
            perception=self.perception,
            tools=self.tools,
            max_rounds=self.config.MAX_TOOL_ROUNDS,
        )
        self.name = self.personality.profile.name

        self.heartbeat = Heartbeat(
            interval_seconds=self.config.HEARTBEAT_INTERVAL_SECONDS,
            on_beat=self._heartbeat_tick,
        )
        self.heartbeat.start()

    @classmethod
    def build_default(cls) -> "SoulCore":
        return cls(model_manager=build_model_manager())

    @catch_and_log(logger, ParseError())
    def step_parse(self, trace_id: str, user_input: str) -> Parse:
        logger.debug(f"[{trace_id}] parse start: {user_input}")
        if self.config.IF_LLM_PARSE and self.model_manager.available_aliases():
            return self.parser.llm_parse(user_input)
        return self.parser.local_parse(user_input)

    @catch_and_log(logger=logger, default_return="这轮处理失败了。")
    def step(self, user_input: str) -> str:
        trace_id = uuid.uuid4().hex[:8]
        parsed = self.step_parse(trace_id=trace_id, user_input=user_input)

        self.emotion.update_emotion(parsed)
        memories = self.memory.recall(query=user_input, limit=4)

        action_result_text = None
        task_result_text = None
        llm_reply = None

        if parsed.intent == "task_plan":
            plan = self.task_planner.plan(user_input)
            task_result_text = self._execute_task_plan(plan)
        elif parsed.action.action_type != "none":
            prepared_action = self._prepare_action_request(parsed)
            action_result = self.controller.execute(prepared_action)
            action_result_text = action_result.message
            self.emotion.react_to_action_result(action_result.success)
        elif self.config.TOOL_AGENT_ENABLED:
            action_result_text, llm_reply = self._run_tool_agent(parsed, memories)

        heartbeat_snapshot = self.heartbeat.snapshot(self.emotion.emotion_state.arousal)
        if llm_reply is None:
            llm_reply = self._maybe_generate_llm_reply(parsed, memories, action_result_text, task_result_text)

        response = self.responder.respond(
            parsed=parsed,
            memories=memories,
            emotion=self.emotion.emotion_state,
            personality=self.personality.profile,
            heartbeat=heartbeat_snapshot,
            action_result=action_result_text,
            llm_reply=llm_reply,
            task_result=task_result_text,
        )
        final = self.personality.adjust(response, self.emotion.emotion_state)

        self.memory.remember_turn(
            user_text=user_input,
            agent_reply=final,
            parsed=parsed,
            emotion_state=self.emotion.emotion_state,
            action_result=action_result_text or task_result_text,
        )

        logger.orchestrator_step(
            trace_id=trace_id,
            process="agent_step",
            params=user_input,
            output={
                "intent": parsed.intent,
                "emotion": self.emotion.describe(),
                "action": parsed.action.action_type,
                "model": self.current_model_summary(),
            },
        )
        return final

    def _prepare_action_request(self, parsed: Parse) -> ActionRequest:
        action = parsed.action
        if action.action_type != "write_file":
            return action

        target = action.target.strip()
        content = str(action.parameters.get("content", "") or "").strip()
        updated_target = self._normalize_write_target(target, parsed.text)
        updated_content = content or self._infer_write_content(parsed.text, updated_target)

        return ActionRequest(
            action_type=action.action_type,
            target=updated_target,
            parameters={**action.parameters, "content": updated_content},
            reason=action.reason,
            requires_confirmation=action.requires_confirmation,
            confidence=action.confidence,
        )

    def _normalize_write_target(self, target: str, user_text: str) -> str:
        if not target:
            return target
        cleaned = target
        if cleaned == "你的自我介绍.txt":
            cleaned = "多伦娜的自我介绍.txt"
        if "桌面" in user_text and not re.match(r"^[A-Za-z]:\\", cleaned, re.IGNORECASE):
            cleaned = cleaned.replace("/", "\\")
            if not cleaned.startswith(("桌面\\", "desktop\\")):
                cleaned = f"桌面\\{cleaned}"
        return cleaned

    def _infer_write_content(self, user_text: str, target: str) -> str:
        if "自我介绍" in user_text or "自我介绍" in target:
            return self._build_self_intro_text()
        return ""

    def _build_self_intro_text(self) -> str:
        return (
            "我是多伦娜，版本 a0.3。\n\n"
            "我习惯按自己的判断说话，也会记住对话里的重要内容。平时我可以处理不少电脑上的日常事务，"
            "比如打开软件、查看窗口、读取或创建文件、整理简单信息。\n\n"
            "我说话偏直接，不喜欢把事情说得太花。多数时候，我会先把事做完，再把结果告诉你。"
        )

    def run_desktop_goal(self, goal: str) -> str:
        return self.desktop_autopilot.run(goal)

    def get_status(self) -> dict[str, object]:
        heartbeat_snapshot = self.heartbeat.snapshot(self.emotion.emotion_state.arousal)
        return {
            "name": self.name,
            "emotion": self.emotion.describe(),
            "heartbeat": heartbeat_snapshot,
            "memory": self.memory.stats(),
            "models": self.model_manager.summary(),
            "capabilities": self.controller.describe_capabilities(),
            "perception": self.perception.describe_capabilities(),
        }

    def list_models(self) -> list[dict[str, str]]:
        return self.model_manager.summary()

    def switch_model(self, alias: str) -> bool:
        return self.model_manager.switch(alias)

    def inspect_screen(self) -> dict:
        return self.perception.inspect().__dict__

    def list_windows(self) -> list[str]:
        return self.perception.list_windows()

    def list_processes(self) -> str:
        return self.controller.execute(ActionRequest(action_type="list_processes")).message

    def recent_tasks(self) -> list[dict]:
        return self.task_planner.list_recent(limit=10)

    def incomplete_tasks(self) -> list[dict]:
        return self.task_planner.list_incomplete(limit=10)

    def current_model_summary(self) -> str:
        profile = self.model_manager.active_profile()
        if profile is None:
            return "local-only"
        return f"{profile.alias}:{profile.model}"

    def stop(self) -> None:
        self.heartbeat.stop()
        self.memory.maintain()

    def _heartbeat_tick(self) -> None:
        self.emotion.heartbeat()
        self.memory.maintain()

    def _execute_task_plan(self, plan: TaskPlan) -> str:
        if not self.config.AUTO_EXECUTE_TASKS:
            return f"任务计划已经生成，共 {len(plan.steps)} 步，但当前配置没有开启自动执行。"

        summaries: list[str] = []
        for step in plan.steps:
            step.status = "running"
            if step.action.action_type == "none":
                step.status = "skipped"
                step.result = "这一步更像说明，没有检测到可执行动作。"
                summaries.append(f"{step.title}: {step.result}")
                continue

            result = self.controller.execute(step.action)
            step.status = "completed" if result.success else "failed"
            step.result = result.message
            self.emotion.react_to_action_result(result.success)
            summaries.append(f"{step.title}: {result.message}")

        self.task_planner.update_plan(plan)
        return f"任务已经执行，共 {len(plan.steps)} 步。结果：{'；'.join(summaries)}"

    def _maybe_generate_llm_reply(
        self,
        parsed: Parse,
        memories,
        action_result: str | None,
        task_result: str | None,
    ) -> str | None:
        if not (self.config.IF_LLM_RESPOND and self.model_manager.available_aliases()):
            return None

        memory_block = "\n".join(f"- {item.summary or item.content}" for item in memories[:4]) or "- 无"
        action_block = action_result or task_result or "无动作"
        prompt = (
            f"{self.personality.system_prompt()}\n"
            f"当前情绪: {self.emotion.describe()}\n"
            f"当前模型: {self.current_model_summary()}\n"
            f"相关记忆:\n{memory_block}\n"
            f"动作反馈: {action_block}\n"
            f"用户输入: {parsed.text}\n"
            "如果用户在要求执行动作，优先基于动作结果回答。"
            " 不要复述工具调用过程，不要输出括号舞台说明，不要硬插入无关记忆。"
            " 请用中文自然回答，简洁、像真人说话。"
        )
        reply = self.model_manager.chat([LLMContent.user_message_standard(prompt)])
        if not reply:
            return None
        return reply.content

    def _run_tool_agent(self, parsed: Parse, memories) -> tuple[str | None, str | None]:
        if not self.model_manager.available_aliases():
            return None, None

        tool_feedback: list[str] = []
        tool_messages: list[dict[str, str]] = []
        for _ in range(self.config.MAX_TOOL_ROUNDS):
            reply = self._ask_model_tool_decision(parsed, memories, tool_feedback, tool_messages)
            if reply is None:
                return ("\n".join(tool_feedback) if tool_feedback else None, None)

            if reply.tool_calls:
                for call in reply.tool_calls:
                    result = self.tools.execute_tool(call.name, call.arguments)
                    self.emotion.react_to_action_result(result.success)
                    tool_feedback.append(f"{call.name}: {result.message}")
                    tool_messages.append(
                        {
                            "role": "tool",
                            "content": json.dumps({"name": call.name, "result": result.message}, ensure_ascii=False),
                        }
                    )
                continue

            if reply.content.strip():
                return ("\n".join(tool_feedback) if tool_feedback else None, reply.content.strip())

            fallback = self._extract_json_object(reply.content)
            if fallback and fallback.get("mode") == "final":
                return ("\n".join(tool_feedback) if tool_feedback else None, fallback.get("message"))
            if fallback and fallback.get("mode") == "tool":
                action_payload = fallback.get("action", {})
                result = self.tools.execute_tool(action_payload.get("action_type", "none"), action_payload)
                self.emotion.react_to_action_result(result.success)
                tool_feedback.append(f"{action_payload.get('action_type', 'none')}: {result.message}")
                continue
            break

        return ("\n".join(tool_feedback) if tool_feedback else None, None)

    def _ask_model_tool_decision(self, parsed: Parse, memories, tool_feedback, tool_messages):
        memory_block = "\n".join(f"- {item.summary or item.content}" for item in memories[:4]) or "- 无"
        feedback_block = "\n".join(f"- {line}" for line in tool_feedback) or "- 暂无"
        base_messages = [
            LLMContent.sys_message_standard(
                f"{self.personality.system_prompt()}\n"
                "你正在做工具决策。"
                " 需要动作时优先调工具；已经足够回答时直接给最终回答。"
                ' 无法原生调工具时，只输出 JSON：{"mode":"tool","action":{...}} 或 {"mode":"final","message":"..."}'
            ),
            LLMContent.user_message_standard(
                f"相关记忆:\n{memory_block}\n已有工具反馈:\n{feedback_block}\n用户输入: {parsed.text}"
            ),
        ]
        messages = base_messages + tool_messages
        return self.model_manager.chat(
            messages,
            temperature=0.2,
            max_tokens=500,
            tools=self.tools.specs(),
        )

    def _extract_json_object(self, text: str) -> dict | None:
        text = (text or "").strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
