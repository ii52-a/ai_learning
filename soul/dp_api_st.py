import os

import dotenv
import requests
import json

from soul.utils.config import InitPersonality
dotenv.load_dotenv()
class DeepSeekClint:
    def __init__(self,
                 api_key:str,
                 base_url:str="https://api.deepseek.com/v1",
                 ):
        self.api_key=api_key
        self.base_url=base_url
        #权限，内容格式
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self,messages,model='deepseek-chat',temperature=0.7,max_tokens=512):
        """

        :param messages: [{"role":"user","content":"hello"}]
        :param model: deepseek-chat/deepseek-reasoner
        :param temperature: 随机性
        :param max_tokens: 最大token输出
        :return: ai返回的文本
        """
        url=f"{self.base_url}/chat/completions"
        init_personality:list=InitPersonality.INIT_PERSONALITY
        payload = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages":init_personality+messages,
        }
        response = requests.post(url=url, headers=self.headers, json=payload)
        response.raise_for_status()
        data=response.json()
        return data['choices'][0]['message']['content']

    def completion(self,prompt,model='deepseek-chat',temperature=0.7,max_tokens=512):
        """
        文本补全模块
        :param max_tokens:
        :param temperature:
        :param prompt:
        :param model:
        :return:
        """
        url=f"{self.base_url}/completions"
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        response = requests.post(url=url, headers=self.headers, json=payload)
        response.raise_for_status()
        data=response.json()
        return data['data']['choices'][0]['text']

    def embeddings(self,text,model='deepseek-embeddings'):
        """
        生成向量
        :param text:
        :param model:
        :return:
        """
        url=f"{self.base_url}/embeddings"
        payload = {
            "model": model,
            "input": text,
        }
        response = requests.post(url=url, headers=self.headers, json=json.dumps(payload))
        response.raise_for_status()
        data=response.json()
        #response["data"][0]["embedding"]
        return data[0]['embeddings']

if __name__ == '__main__':
    api=os.getenv("DEEPSEEK_API_KEY")
    print(api)
    a=DeepSeekClint(api_key=api)
    str_ai=[{"role":"user","content":f"{input()}"}]
    print(a.chat(str_ai))