
from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import EmotionState

logger = Logger(__name__)
class Emotion:
    def __init__(self):
        self.emotion_state:EmotionState =EmotionState(
            valence=0.5,
            arousal=0.5
        )

    @catch_and_log(logger)
    def update_emotion(self,parsed) -> None:
        self.emotion_state.valence+=0.01