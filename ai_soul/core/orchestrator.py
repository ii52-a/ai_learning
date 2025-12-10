"""调度,负责各个模块的组合使用"""
import os

import dotenv

import dp_api_st
class SourCore:
    def __init__(self,llm):
        self.llm = llm

        #单指用户，以后拓展至人际关系，独立为情绪状态模块
        self.user_status={
            'emotion':'neutral',
        }

        self.mine_status={
            'emotion':'happy',
        }


    def cycle(self,user_input:str):
        if '累' in user_input:
            self.user_status['emotion']='tired'
        if '开心' in user_input:
            self.user_status['emotion']='happy'

        content=f"[user_status]:{self.user_status['emotion']} [your_status]:{self.mine_status['emotion']}"
        messages=[
            {'role':'system','content':content},
            {
                'role':'user','content':user_input,
            }
        ]
        return self.llm.chat(messages)

if __name__ == '__main__':
    dotenv.load_dotenv()
    api_key=os.getenv("DEEPSEEK_API_KEY")
    brain=dp_api_st.DeepSeekClint(api_key)
    sour=SourCore(brain)
    while True:
        ai=sour.cycle(input("you:"))
        print("多伦娜a0.1:",ai)


