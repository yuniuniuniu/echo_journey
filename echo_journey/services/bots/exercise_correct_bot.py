from echo_journey.data.whole_context import WholeContext
import os
import logging
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

class CorrectBot():
    def __init__(self):
        self.context = WholeContext.generate_context_by_json(os.getenv("CorrectBotPath"), "correct_bot")
        self.finals_oss_path = os.getenv("FINALS_OSS_PATH")
        self.initials_oss_path = os.getenv("INITIALS_OSS_PATH")
        self.success_score = 90
        self.three_syllable_split_dict = self.init_three_syllable_split_info()
        
    def init_three_syllable_split_info(self):
        import json
        with open("echo_journey/services/bots/meta/three_syllable_split.json", "r") as f:
            json_data = json.load(f)
            return json_data
        
    def find_error(self, expected_messages, messages):
        result = {}
        try:
            for index, expected_message in enumerate(expected_messages):
                if index >= len(messages):
                    break
                else:
                    message = messages[index]
                    if expected_message.initial_consonant != message.initial_consonant and expected_message.initial_consonant:
                        key = f"声母 {expected_message.initial_consonant}"
                        result[key] = self.initials_oss_path + expected_message.initial_consonant + ".mp4"
                        
                    if expected_message.vowels != message.vowels and expected_message.vowels:
                        if expected_message.vowels in self.three_syllable_split_dict:
                            if message.vowels and message.vowels in self.three_syllable_split_dict:
                                exp_vowels0 = self.three_syllable_split_dict[expected_message.vowels][0]
                                exp_vowels1 = self.three_syllable_split_dict[expected_message.vowels][1]
                                vowels0 = self.three_syllable_split_dict[message.vowels][0]
                                vowels1 = self.three_syllable_split_dict[message.vowels][1]
                                if exp_vowels0 != vowels0:
                                    key = f"韵母 {exp_vowels0}"
                                    result[key] = self.finals_oss_path + exp_vowels0 + ".mp4"
                                if exp_vowels1 != vowels1:
                                    key = f"韵母 {exp_vowels1}"
                                    result[key] = self.finals_oss_path + exp_vowels1 + ".mp4"
                                
                            else:
                                for vowel in self.three_syllable_split_dict[expected_message.vowels]:
                                    key = f"韵母 {vowel}"
                                    result[key] = self.finals_oss_path + vowel + ".mp4"
                        else:
                            key = f"韵母 {expected_message.vowels}"
                            result[key] = self.finals_oss_path + expected_message.vowels + ".mp4"
        except Exception as e:
            logger.error(f"error: {e}")
            logger.error(f"expected_messages: {expected_messages}")
            logger.error(f"messages: {messages}")
        return result
            
    async def get_correct_result(self, expected_messages, messages):
        format_dict = self.format_correct_bot_input(expected_messages, messages)
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        result =  await self.context.execute()
        suggestions = ""
        name_2_mp4_url = self.find_error(expected_messages, messages)
        try:
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
        return suggestions, score, name_2_mp4_url
    
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