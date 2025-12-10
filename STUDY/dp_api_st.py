import requests
import json

class DeepSeekClint:
    def __init__(self,
                 api_key:str,
                 base_url:str="https://api.deepseek.com/v1",
                 ):
        self.api_key=api_key
        self.base_url=base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self,messages,model='deepseek-chat',temperature=0.7,max_token=512):
        """

        :param message: [{"role":"user","Content":"hello"}]
        :param model: deepseek-chat deepseek-reasoner
        :param temperature: 随机性
        :param max_token: 最大token输出
        :return: ai返回的文本
        """
        url=f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "temperature": temperature,
            "max_token": max_token,
            "message": messages,
        }
        response = requests.post(url=url, headers=self.headers, json=json.dumps(payload))
        response.raise_for_status()
        data=response.json()
        return data['choices'][0]['message']['content']

    def completion(self,prompt,model='deepseek-chat',temperature=0.7,max_token=512):
        """
        文本补全模块
        :param prompt:
        :param model:
        :return:
        """
        url=f"{self.base_url}/completions"
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_token": max_token,
        }
        response = requests.post(url=url, headers=self.headers, json=json.dumps(payload))
        response.raise_for_status()
        data=response.json()
        return data['choices'][0]['text']

    def enbeddings(self,text,model='deepseek-enbeddings'):
        """
        生成向量
        :param prompt:
        :param model:
        :return:
        """
        url=f"{self.base_url}/enbeddings"
        payload = {
            "model": model,
            "input": text,
        }
        response = requests.post(url=url, headers=self.headers, json=json.dumps(payload))
        response.raise_for_status()
        data=response.json()
        return data[0]['enbeddings']