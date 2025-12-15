"""调度,负责各个模块的组合使用"""
import os
import uuid

import dotenv

from soul import dp_api_st
from soul.modules.emotion import Emotion
from soul.modules.memory import Memory
from soul.modules.nlp_parser import LLMParser
from soul.modules.personality import Personality
from soul.modules.responder import Responder
from soul.utils.decorator import catch_and_log

from soul.utils.logger import Logger
from soul.utils.type import Parse, ParseError
from soul.utils.util import LLMContent
logger=Logger(__name__)
dotenv.load_dotenv()

class SourCore:
    def __init__(self,llm,parser,emotion,memory,personality,responder):
        self.llm = llm
        self.parser:LLMParser = parser
        self.emotion:Emotion = emotion
        self.memory:Memory = memory
        self.personality:Personality = personality
        self.responder:Responder = responder
        self.name:str="多伦娜a0.2"


    def local_model(self,trace_id,parsed,memory:Memory,emotion:Emotion) ->str:
        #格式化回复
        raw_reply=self.responder.respond(parsed,memory,emotion.emotion_state)
        logger.orchestrator_step(trace_id=trace_id,
                                 process="responder,respond思考模块",
                                 params=(parsed,self.memory,self.emotion.emotion_state),
                                 output=raw_reply,
                                 )

        #性格调控
        final=self.personality.adjust(raw_reply,self.emotion.emotion_state)
        return final

    def llm_model(self,trace_id,parsed,memory:Memory,emotion:Emotion) ->str:
        inpu=LLMContent.sys_user_message_standard(parsed,parsed.text)
        logger.info(inpu)
        final=self.llm.chat(inpu)
        return final

    @catch_and_log(logger=logger,default_return="step错误")
    def step(self,user_input:str) -> any:
        trace_id = uuid.uuid4().hex[:8]

        logger.debug(f"[{trace_id}] [CORE] step start | user_input='{user_input}'")
        #语义拆解
        parsed:Parse=self.parser.parse(user_input)
        if type(parsed) is ParseError:
            logger.warning(f"[{trace_id}] [CORE] step parse error")
        logger.orchestrator_step(trace_id=trace_id,
                                 process="parser,parse语义模块",
                                 params=user_input,
                                 output=parsed,
                                 )

        #情绪更新
        self.emotion.update_emotion(parsed)
        logger.orchestrator_step(trace_id=trace_id,
                                 process="emotion,update_emotion情绪模块",
                                 params=parsed,
                                 output=None
                                 )
        #更新记忆

        self.memory.remember(parsed)
        logger.orchestrator_step(trace_id=trace_id,
                                 process="memory,remember记忆模块",
                                 params=parsed,
                                 output=None
                                 )


        final=self.llm_model(trace_id,parsed,memory,emotion)
        return final

if __name__ == '__main__':
    dotenv.load_dotenv()
    api_key=os.getenv("DEEPSEEK_API_KEY")

    llm= dp_api_st.DeepSeekClint(api_key)

    emotion=Emotion()
    memory=Memory()
    nlp_parse=LLMParser(llm)
    personality=Personality()
    responder=Responder()



    sour=SourCore(llm,nlp_parse,emotion,memory,personality,responder)
    while True:
        ai_reply=sour.step(input("you:"))
        print(f"{sour.name}:{ai_reply}")


