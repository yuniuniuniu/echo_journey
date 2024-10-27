import copy
import json
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
        self.system_template = copy.deepcopy(self.context.cur_visible_assistant.content.system_prompt)
        self.final_pron_dict, self.initial_pron_dict = self.init_pron_info()
        
    def init_pron_info(self):
        with open("echo_journey/services/bots/meta/finals_pron.json", 'r') as f:
            finals_pron_dict = json.load(f)
        with open("echo_journey/services/bots/meta/initials_pron.json", 'r') as f:
            initials_pron_dict = json.load(f)
        return finals_pron_dict, initials_pron_dict
        
    def init_three_syllable_split_info(self):
        import json
        with open("echo_journey/services/bots/meta/three_syllable_split.json", "r") as f:
            json_data = json.load(f)
            return json_data
        
    def _personal_context_by(self, related_initials, related_vowels):
        initials_str = ""
        finals_str = ""
        for initial in related_initials:
            if initial in self.initial_pron_dict:
                pron = self.initial_pron_dict[initial]
                initials_str += f"{initial}: {pron}\n"
        for vowel in related_vowels:
            if vowel in self.final_pron_dict:
                pron = self.final_pron_dict[vowel]
                finals_str += f"{vowel}: {pron}\n"
        if not initials_str:
            initials_str = "暂时未发现学生的声母错误"
        if not finals_str:
            finals_str = "暂时未发现学生的韵母错误"
        self.context.cur_visible_assistant.content.system_prompt = self.system_template.replace(r"""{initials}""", initials_str)   
        self.context.cur_visible_assistant.content.system_prompt = self.context.cur_visible_assistant.content.system_prompt.replace(r"""{finals}""", finals_str)
           
        
    def find_error(self, expected_messages, messages):
        related_initials = set()
        related_vowels = set()
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
                        related_initials.add(expected_message.initial_consonant)
                        related_initials.add(message.initial_consonant)
                        
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
                                    related_vowels.add(exp_vowels0)
                                    related_vowels.add(vowels0)
                                if exp_vowels1 != vowels1:
                                    key = f"韵母 {exp_vowels1}"
                                    result[key] = self.finals_oss_path + exp_vowels1 + ".mp4"
                                    related_vowels.add(exp_vowels1)
                                    related_vowels.add(vowels1)
                                
                            else:
                                for vowel in self.three_syllable_split_dict[expected_message.vowels]:
                                    key = f"韵母 {vowel}"
                                    result[key] = self.finals_oss_path + vowel + ".mp4"
                                    related_vowels.add(vowel)
                                related_vowels.add(message.vowels)
                        else:
                            key = f"韵母 {expected_message.vowels}"
                            result[key] = self.finals_oss_path + expected_message.vowels + ".mp4"
                            related_vowels.add(expected_message.vowels)
                            related_vowels.add(message.vowels)
        except Exception as e:
            logger.error(f"error: {e}")
            logger.error(f"expected_messages: {expected_messages}")
            logger.error(f"messages: {messages}")
        return result, related_initials, related_vowels
    
    def _is_sentence_equal(self, expected_message_str, messages_str):
        return expected_message_str == messages_str
            
    async def get_correct_result(self, expected_messages, messages):
        name_2_mp4_url, related_initials, related_vowels  = self.find_error(expected_messages, messages)
        self._personal_context_by(related_initials, related_vowels)
        format_dict = self.format_correct_bot_input(expected_messages, messages)
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        logger.info(f"exercise correct bot user_msg: {user_msg}")
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        result =  await self.context.execute()
        logger.info(f"exercise correct bot result: {result}")
        suggestions = ""

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
        
        if self._is_sentence_equal(expected_words, words):
            score = 100
        
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