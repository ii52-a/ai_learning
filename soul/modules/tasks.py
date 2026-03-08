from __future__ import annotations

import json
import re
from pathlib import Path

from soul.modules.nlp_parser import Parser
from soul.utils.config import InitConfig, TASKS_FILE
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import TaskPlan, TaskStep

logger = Logger(__name__)


class TaskPlanner:
    def __init__(self, parser: Parser, storage_path: Path | None = None, config: InitConfig | None = None):
        self.parser = parser
        self.config = config or InitConfig()
        self.storage_path = Path(storage_path or TASKS_FILE)
        self.config.ensure_runtime()

    def plan(self, text: str) -> TaskPlan:
        clauses = self._split_clauses(text)
        steps: list[TaskStep] = []
        for index, clause in enumerate(clauses, start=1):
            parsed = self.parser.local_parse(clause)
            steps.append(
                TaskStep(
                    title=f"步骤 {index}: {clause[:18]}",
                    instruction=clause,
                    action=parsed.action,
                )
            )

        if not steps:
            parsed = self.parser.local_parse(text)
            steps.append(TaskStep(title="步骤 1", instruction=text, action=parsed.action))

        plan = TaskPlan(goal=text, steps=steps, source="local")
        self._persist_plan(plan)
        return plan

    @catch_and_log(logger, [])
    def list_recent(self, limit: int = 10) -> list[dict]:
        if not self.storage_path.exists():
            return []
        payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        return payload[-limit:]

    def update_plan(self, plan: TaskPlan) -> None:
        records = self.list_recent(limit=100)
        updated = False
        for idx, record in enumerate(records):
            if record.get("plan_id") == plan.plan_id:
                records[idx] = plan.to_dict()
                updated = True
                break
        if not updated:
            records.append(plan.to_dict())
        self.storage_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_plan(self, plan_id: str) -> dict | None:
        records = self.list_recent(limit=200)
        for record in records:
            if record.get("plan_id") == plan_id:
                return record
        return None

    def list_incomplete(self, limit: int = 10) -> list[dict]:
        records = self.list_recent(limit=100)
        incomplete: list[dict] = []
        for record in reversed(records):
            steps = record.get("steps", [])
            if any(step.get("status") in {"pending", "running", "failed"} for step in steps):
                incomplete.append(record)
            if len(incomplete) >= limit:
                break
        return incomplete

    def _persist_plan(self, plan: TaskPlan) -> None:
        records = self.list_recent(limit=100)
        records.append(plan.to_dict())
        self.storage_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def _split_clauses(self, text: str) -> list[str]:
        stripped = text.strip()
        if stripped.startswith("任务"):
            stripped = stripped.lstrip("任务:： ")
        parts = re.split(r"(?:然后|再|接着|之后|并且|同时|；|;|\n)", stripped)
        return [part.strip(" ，。！？,.!?") for part in parts if part.strip(" ，。！？,.!?")]
