"""调度,负责各个模块的组合使用"""
import os
import uuid

import dotenv

from soul import dp_api_st
from soul.modules.emotion import Emotion
from soul.modules.memory import Memory
from soul.modules.nlp_parser import NlpParser
from soul.modules.personality import Personality
from soul.modules.responder import Responder


from soul.utils.logger import Logger

logger=Logger(__name__)
dotenv.load_dotenv()

class SourCore:
    def __init__(self,llm,parser,emotion,memory,personality,responder):
        self.llm = llm
        self.parser:NlpParser = parser
        self.emotion:Emotion = emotion
        self.memory:Memory = memory
        self.personality:Personality = personality
        self.responder:Responder = responder
        self.name:str="多伦娜a0.1"




    def step(self,user_input:str) -> any:
        trace_id = uuid.uuid4().hex[:8]

        logger.info(f"[{trace_id}] [CORE] step start | user_input='{user_input}'")
        #语义拆解
        parsed=self.parser.parse(user_input)
        logger.orchestrator_step(trace_id=trace_id,
                                 process="parser,parse",
                                 params=user_input,
                                 output=parsed,
                                 )

        #情绪更新
        self.emotion.update_emotion(parsed)
        logger.orchestrator_step(trace_id=trace_id,
                                 process="emotion,update_emotion",
                                 params=parsed,
                                 output=None
                                 )
        #更新记忆

        self.memory.remember(parsed)
        logger.orchestrator_step(trace_id=trace_id,
                                 process="memory,remember",
                                 params=parsed,
                                 output=None
                                 )

        #格式化回复
        raw_reply=self.responder.respond(parsed,self.memory,self.emotion.emotion_state)
        logger.orchestrator_step(trace_id=trace_id,
                                 process="responder,respond",
                                 params=(parsed,self.memory,self.emotion.emotion_state),
                                 output=raw_reply,
                                 )

        #性格调控
        final=self.personality.adjust(raw_reply,self.emotion.emotion_state)

        return final

if __name__ == '__main__':
    dotenv.load_dotenv()
    api_key=os.getenv("DEEPSEEK_API_KEY")

    llm= dp_api_st.DeepSeekClint(api_key)
    emotion=Emotion()
    memory=Memory()
    nlp_parse=NlpParser()
    personality=Personality()
    responder=Responder()



    sour=SourCore(llm,nlp_parse,emotion,memory,personality,responder)
    while True:
        ai_reply=sour.step(input("you:"))
        print(f"{sour.name}:{ai_reply}")


