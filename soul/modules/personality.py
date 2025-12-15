class Personality:

    @staticmethod
    def adjust(text,emotion_state) -> str:
        if emotion_state['valence'] >=0.6:
            return text+ '^_^'
        return text