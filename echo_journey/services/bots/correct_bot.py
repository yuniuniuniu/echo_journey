from echo_journey.data.learn_situation import LearnSituation
from echo_journey.data.practise_progress import PractiseProgress
from echo_journey.data.whole_context import WholeContext
import os
import logging
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

class CorrectBot():
    def __init__(self, learn_situation: LearnSituation, practise_progress: PractiseProgress):
        self.learn_situation = learn_situation
        self.practise_progress = practise_progress
        self.context = WholeContext.generate_context_by_json(os.getenv("CorrectBotPath"), "correct_bot")
        self.success_score = 90
        
    async def get_correct_result(self, expected_messages, messages):
        format_dict = self.format_correct_bot_input(expected_messages, messages)
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        result =  await self.context.execute()
        suggestions = ""
        try:
            # problem = result.get("problem", None)
            # if not problem:
            #     problem = ""
            # suggestions += problem + "\n"
            suggestion_dict = result.get("suggestion_dict", None)
            for term, suggestion in suggestion_dict.items():
                suggestions += f"- {term}: {suggestion}\n"
        except Exception as e:
            logger.error(f"error: {e}")
            logger.error(f"result: {result}")
        logger.info(result)
        score = int(result["score"])
        expected_words = ""
        words = ""
        for expected_message in expected_messages:
            expected_words += expected_message.word
        for message in messages:
            words += message.word
        if score <= self.success_score:
            self.learn_situation.update(self.practise_progress.get_scene(), expected_words, words)
        return suggestions, score, result.get("change_scene", False)
    
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