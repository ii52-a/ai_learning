from __future__ import annotations

import json
import os

import requests
from requests import RequestException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from soul.llm.base import BaseChatModel
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import ModelProfile, ModelResponse, ToolCall, ToolSpec

logger = Logger(__name__)


class OpenAICompatibleModel(BaseChatModel):
    def __init__(self, profile: ModelProfile) -> None:
        super().__init__(profile)
        api_key = os.getenv(profile.api_key_env, "")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(RequestException),
    )
    @catch_and_log(logger, None)
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse | None:
        endpoint = f"{self.profile.base_url.rstrip('/')}/chat/completions"
        payload: dict[str, object] = {
            "model": self.profile.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = [tool.to_openai_tool() for tool in tools]
            payload["tool_choice"] = "auto"

        response = requests.post(endpoint, headers=self.headers, json=payload, timeout=60)
        response.raise_for_status()
        raw = response.json()
        choice = raw["choices"][0]
        message = choice["message"]
        tool_calls: list[ToolCall] = []
        for tool_call in message.get("tool_calls", []) or []:
            function = tool_call.get("function", {})
            try:
                arguments = json.loads(function.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(
                ToolCall(
                    name=function.get("name", ""),
                    arguments=arguments,
                    call_id=tool_call.get("id", ""),
                )
            )
        return ModelResponse(
            content=message.get("content", "") or "",
            provider=self.profile.provider,
            model=self.profile.model,
            raw=raw,
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
        )


class OllamaModel(BaseChatModel):
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(RequestException),
    )
    @catch_and_log(logger, None)
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse | None:
        endpoint = f"{self.profile.base_url.rstrip('/')}/api/chat"
        payload: dict[str, object] = {
            "model": self.profile.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = [tool.to_openai_tool()["function"] for tool in tools]
        response = requests.post(endpoint, data=json.dumps(payload), timeout=90)
        response.raise_for_status()
        raw = response.json()
        message = raw.get("message", {})
        tool_calls: list[ToolCall] = []
        for tool_call in message.get("tool_calls", []) or []:
            function = tool_call.get("function", {})
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            tool_calls.append(
                ToolCall(
                    name=function.get("name", ""),
                    arguments=arguments,
                    call_id=tool_call.get("id", ""),
                )
            )
        return ModelResponse(
            content=message.get("content", "") or "",
            provider=self.profile.provider,
            model=self.profile.model,
            raw=raw,
            tool_calls=tool_calls,
            finish_reason=raw.get("done_reason", "stop"),
        )

