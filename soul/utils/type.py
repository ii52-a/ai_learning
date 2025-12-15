from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class EmotionState:
    valence: float = 0.5
    arousal: float = 0.5


@dataclass
class Entity:
    type: str = None
    value: str = None


# 语义拆解组
@dataclass
class Parse:
    text: str
    intent: Optional[str] = None  # 用户意图
    entities: List[Entity] = field(default_factory=list)  # 涉及对象
    sentiment: Optional[str] = None  # 情绪附加

class ParseError:
    text: str="Parse error"
    intent: Optional[str] = None
    entities: List[Entity] = field(default_factory=list)
    sentiment: Optional[str] = None
@dataclass
class MemoryType:
    memory: List[Parse] = field(default_factory=list)
