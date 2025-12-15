
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import Parse

logger=Logger(__name__)
class LLMContent:

    @staticmethod
    def sys_message_standard(parse:Parse) -> dict:
        return {"role":"system","content":str(parse)}

    @staticmethod
    def user_message_standard(text: str) -> dict:
        return {"role": "user", "content": text}

    @classmethod
    def sys_user_message_standard(cls,parse:Parse,text2:str) -> list[dict]:
        return [cls.sys_message_standard(parse), cls.user_message_standard(text2)]

    @classmethod
    @catch_and_log(logger=logger)
    def get_parse_input_text(cls,text,chose='user'):
        if chose=='user':
            PARSE_INPUT_TEXT = f"""
               你是一个语义分析模块。
               你的任务是把用户输入解析为 JSON。
               不要解释，不要多余文本。
               输出字段：
               {{
                   "intent": string,
                   "sentiment": string,
                   "entities": [
                       {{
                           "type": string,
                           "value": string
                       }}
                       ]
               }}
               用户输入：
               {text}
    
               不要使用 Markdown
               不要使用 ```json
               只输出纯 JSON 文本
               """
            user_input=cls.user_message_standard(PARSE_INPUT_TEXT)
        else:
            user_input=cls.user_message_standard(text)
        return user_input
