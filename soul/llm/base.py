from __future__ import annotations

from abc import ABC, abstractmethod

from soul.utils.type import ModelProfile, ModelResponse, ToolSpec


class BaseChatModel(ABC):
    def __init__(self, profile: ModelProfile) -> None:
        self.profile = profile

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse | None:
        raise NotImplementedError

