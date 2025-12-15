from logging import exception


from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import EmotionState

logger=Logger(__name__)
class Personality:

    @staticmethod
    @catch_and_log(logger, exception)
    def adjust(text,emotion_state:EmotionState) -> str:
        if emotion_state.valence >=0.6:
            return text+ '^_^'
        return text