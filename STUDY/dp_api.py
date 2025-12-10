# deepseek_chat.py

import os
import requests
import json
import dotenv
dotenv.load_dotenv()
# —— 配置 ——
API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 你可以把 key 放到环境变量里
# 或者直接写成字符串： API_KEY = "your_real_key"

BASE_URL = "https://api.deepseek.com"  # 官方 base_url :contentReference[oaicite:1]{index=1}
MODEL = "deepseek-chat"  # 或 "deepseek-reasoner" / 根据你权限 / 需求选择 :contentReference[oaicite:2]{index=2}

# —— 对话环境和函数 ——
def chat(messages, max_tokens=512, temperature=0.7, stream=False):
    """
    messages: list of dict, 每个 dict 形如 {"role": "user"/"system"/"assistant", "content": str}
    返回模型 reply 的文本
    """
    url = BASE_URL + "/chat/completions"
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # 假设不使用 stream，直接取第一个 choice 的内容
    return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    print("=== DeepSeek Chat 模式 ===")
    history = []
    # 可以预设 system prompt
    history.append({"role": "system", "content": "You are a helpful assistant."})

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Bye")
            break
        history.append({"role": "user", "content": user_input})
        try:
            reply = chat(history)
        except Exception as e:
            print("Error:", e)
            break
        print("Bot:", reply)
        history.append({"role": "assistant", "content": reply})
