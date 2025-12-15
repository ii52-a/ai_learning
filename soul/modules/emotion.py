from soul.utils.type import EmotionState


class Emotion:
    def __init__(self):
        self.emotion_state:EmotionState =EmotionState(
            valence=0.5,
            arousal=0.5
        )
    def update_emotion(self,parsed) -> None:
        self.emotion_state.valence+=0.01