from soul.modules.memory import Memory
from soul.utils.type import Parse


class Responder:

    @staticmethod
    def respond(parsed:Parse,
                memory:Memory,
                emotion,
                ) -> str:
        base=f"你说了:{parsed.text}"
        last_memory:list[Parse]=memory.recall()
        if last_memory:
            base+=f"(我记得你刚刚说过:{last_memory[0].text})"
        return base