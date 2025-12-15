from typing import List

from soul.utils.type import Parse, MemoryType


class Memory:
    def __init__(self):
        self._memory:MemoryType = MemoryType()

    def remember(self,parsed:Parse) -> None:
        self._memory.memory.append(parsed)


    #TODO:当前默认是上一条，需要修改适配性
    def recall(self,last_number:int=1) -> List[Parse]:
        return self._memory[-last_number:]