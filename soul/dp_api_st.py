from __future__ import annotations

from soul.llm.providers import OpenAICompatibleModel
from soul.utils.type import ModelProfile, ModelResponse


class DeepSeekClint(OpenAICompatibleModel):
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1") -> None:
        # 兼容旧调用入口，内部走统一 provider 实现。
        profile = ModelProfile(
            alias="deepseek",
            provider="deepseek",
            model="deepseek-chat",
            base_url=base_url,
            api_key_env="DEEPSEEK_API_KEY",
        )
        super().__init__(profile)
        self.headers["Authorization"] = f"Bearer {api_key}"

    def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 700,
    ) -> dict | None:
        self.profile.model = model
        response: ModelResponse | None = super().chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response is None:
            return None
        return {"role": "assistant", "content": response.content}

