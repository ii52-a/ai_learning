from dataclasses import dataclass, field
from typing import List,Dict,Optional
@dataclass
class EmotionState:
    valence: float=0.5
    arousal: float=0.5





#语义拆解组
@dataclass
class Parse:
    text: str

@dataclass
class MemoryType:
    memory: List[Parse]=field(default_factory=list)