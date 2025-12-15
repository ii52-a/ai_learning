import json

from soul.utils.decorator import catch_and_log
from soul.utils.logger import Logger
from soul.utils.type import Parse, Entity, ParseError
from soul.utils import util
logger=Logger(__name__)
class LLMParser:
    def __init__(self,llm_client):
        self.llm_client = llm_client


    @catch_and_log(logger,ParseError)
    def parse(self,text:str) -> Parse:

        parse_str=self.llm_client.chat(
            [util.LLMContent.get_parse_input_text(text)]
        )
        logger.start_debug(parse_str)
        parse=json.loads(parse_str)

        logger.info(parse)

        entities = []
        for e in parse.get("entities", []):
            entities.append(
                Entity(
                    type=e.get("type"),
                    value=e.get("value")
                )
            )
        return Parse(
            text=text,
            intent=parse["intent"],
            entities=entities,
            sentiment=parse["sentiment"],
        )
