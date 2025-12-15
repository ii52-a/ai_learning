from logging import exception

from soul.modules.memory import Memory
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import Parse

logger=Logger(__name__)
class Responder:

    @staticmethod
    @catch_and_log(logger, exception)
    def respond(parsed:Parse,
                memory:Memory,
                emotion,
                ) -> str:
        base=f"你说了:{parsed.text}"
        last_memory:list[Parse]=memory.recall()
        if last_memory:
            base+=f"(我记得你刚刚说过:{last_memory[0].text})"
        return base