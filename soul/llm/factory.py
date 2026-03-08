from __future__ import annotations

import os

from soul.llm.base import BaseChatModel
from soul.llm.providers import OllamaModel, OpenAICompatibleModel
from soul.utils.config import InitConfig
from soul.utils.type import ModelProfile, ModelResponse, ToolSpec


class ModelManager:
    def __init__(self, profiles: list[ModelProfile], active_alias: str = "") -> None:
        self.profiles = {profile.alias: profile for profile in profiles if profile.enabled}
        self.clients: dict[str, BaseChatModel] = {}
        for alias, profile in self.profiles.items():
            if profile.provider in {"deepseek", "openai", "openai_compatible"}:
                self.clients[alias] = OpenAICompatibleModel(profile)
            elif profile.provider == "ollama":
                self.clients[alias] = OllamaModel(profile)

        self.active_alias = active_alias or next(iter(self.clients), "")

    def available_aliases(self) -> list[str]:
        return list(self.clients.keys())

    def active_profile(self) -> ModelProfile | None:
        if not self.active_alias:
            return None
        return self.profiles.get(self.active_alias)

    def switch(self, alias: str) -> bool:
        if alias not in self.clients:
            return False
        self.active_alias = alias
        return True

    def summary(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for alias, profile in self.profiles.items():
            rows.append(
                {
                    "alias": alias,
                    "provider": profile.provider,
                    "model": profile.model,
                    "base_url": profile.base_url,
                    "active": "yes" if alias == self.active_alias else "no",
                }
            )
        return rows

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 700,
        tools: list[ToolSpec] | None = None,
    ) -> ModelResponse | None:
        if not self.active_alias:
            return None
        client = self.clients.get(self.active_alias)
        if client is None:
            return None
        return client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
        )


def build_model_manager(config: InitConfig | None = None) -> ModelManager:
    config = config or InitConfig()
    profiles: list[ModelProfile] = []

    if os.getenv("DEEPSEEK_API_KEY"):
        profiles.append(
            ModelProfile(
                alias="deepseek",
                provider="deepseek",
                model=os.getenv("DEEPSEEK_MODEL", config.DEFAULT_MODEL_NAME or "deepseek-chat"),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                api_key_env="DEEPSEEK_API_KEY",
                supports_vision=False,
            )
        )

    if os.getenv("OPENAI_API_KEY"):
        profiles.append(
            ModelProfile(
                alias="openai",
                provider="openai",
                model=os.getenv("OPENAI_MODEL", config.DEFAULT_MODEL_NAME or "gpt-4o-mini"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key_env="OPENAI_API_KEY",
                supports_vision=True,
            )
        )

    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model = os.getenv("OLLAMA_MODEL")
    if ollama_model:
        profiles.append(
            ModelProfile(
                alias="ollama",
                provider="ollama",
                model=ollama_model,
                base_url=ollama_base,
                api_key_env="",
                supports_vision=False,
            )
        )

    active_alias = config.ACTIVE_MODEL_ALIAS
    if not active_alias and config.DEFAULT_PROVIDER:
        provider_map = {
            "deepseek": "deepseek",
            "openai": "openai",
            "openai_compatible": "openai",
            "ollama": "ollama",
        }
        active_alias = provider_map.get(config.DEFAULT_PROVIDER, "")

    return ModelManager(profiles=profiles, active_alias=active_alias)
