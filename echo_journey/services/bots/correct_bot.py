from echo_journey.data.whole_context import WholeContext
import os
import logging
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

class CorrectBot():
    def __init__(self):
        self.context = WholeContext.generate_context_by_json(os.getenv("CorrectBotPath"), "correct_bot")
        
    async def get_correct_result(self, expected_messages, messages):
        format_dict = self.format_correct_bot_input(expected_messages, messages)
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        result =  await self.context.execute()
        suggestions = ""
        try:
            for suggestion in result["suggestion_list"]:
                if not suggestion or suggestion == "null":
                    continue
                else:
                    suggestions += str(suggestion) + "\n"
        except Exception as e:
            logger.error(f"error: {e}")
            logger.error(f"result: {result}")
        logger.info(result)
        return suggestions, int(result["score"])
    
    def format_correct_bot_input(self, expected_messages, messages):
        format_dict = {}
        expected_sentence = ""
        for expected_message in expected_messages:
            expected_sentence += expected_message.word
            expected_sentence += expected_message.pinyin
            expected_sentence += str(expected_message.tone)
            
        sentence = ""
        for message in messages:
            sentence += message.word
            sentence += message.pinyin
            sentence += str(message.tone)
        format_dict["expected_sentence"] = expected_sentence
        format_dict["sentence"] = sentence
        return format_dict