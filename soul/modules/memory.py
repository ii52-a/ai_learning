
from typing import List

from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import Parse, MemoryType

logger = Logger(__name__)
@catch_and_log(logger, None)
class Memory:
    def __init__(self):
        self._memory:MemoryType = MemoryType()

    def remember(self,parsed:Parse) -> None:
        try:
            self._memory.memory.append(parsed)
        except Exception as e:
            logger.error(e)


    #TODO:当前默认是上一条，需要修改适配性
    def recall(self,last_number:int=1) -> List[Parse]:
        return self._memory.memory[-last_number:]