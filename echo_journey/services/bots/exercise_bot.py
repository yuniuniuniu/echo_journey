import logging
from echo_journey.audio.text_to_speech.kanyun_tts import KanyunTTS
from echo_journey.common.utils import parse_pinyin
from echo_journey.data.learn_situation import HistoryLearnSituation
from echo_journey.data.whole_context import WholeContext
import os
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


class ExerciseBot():
    def __init__(self, ws_msg_handler):
        self.context = WholeContext.generate_context_by_json(os.getenv("ExerciseBotPath"), "exercise_bot")
        self.personal_context()
        self.ws_msg_handler = ws_msg_handler
        self.tts: KanyunTTS = KanyunTTS.get_instance()
        self.current_exercise = None
        
        
    def personal_context(self):
        unfamilier_finals_and_initials = HistoryLearnSituation().build_unfamilier_finals_and_initials()
        unfamilier_initials_list = list(unfamilier_finals_and_initials["initials"].keys())
        unfamilier_initials_str = ",".join(unfamilier_initials_list) if unfamilier_initials_list else "无"
        unfamilier_finals_list = list(unfamilier_finals_and_initials["finals"].keys())
        unfamilier_finals_str = ",".join(unfamilier_finals_list) if unfamilier_finals_list else "无"
        self.context.cur_visible_assistant.content.system_prompt = self.context.cur_visible_assistant.content.system_prompt.replace("""{initials}""", unfamilier_initials_str)
        self.context.cur_visible_assistant.content.system_prompt = self.context.cur_visible_assistant.content.system_prompt.replace("""{finals}""", unfamilier_finals_str)
        
    async def send_treating_msg(self, treating_msg, platform):
        self.context.add_user_msg_to_cur({"role": "assistant", "content": "treating_msg"})
        await self.ws_msg_handler.send_tutor_message(text=treating_msg)
        # user_input = ""
        # await self.send_practise_msg(user_input, platform)        
        
    def build_input_by(self, student_text):
        format_dict = {}
        format_dict["STUDENT"] = student_text
        logger.info(f"format_dict: {format_dict}")
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        return user_msg
    
    async def generate_practise_reply(self, student_text):
        user_msg = self.build_input_by(student_text)
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        teacher_info = await self.context.execute()
        return teacher_info
    
    def add_suggestion_to_context(self, suggestions):
        import json
        user_msg = self.build_input_by("老师帮我纠下音吧")
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        assistant_msg = json.dumps({"should_generate": False, "level": None, "new_practise": None, "teacher": suggestions}, ensure_ascii=False)
        self.context.add_assistant_msg_to_cur({"role": "assistant", "content": assistant_msg})
        
    async def send_practise_msg(self, student_text, platform):
        teacher_info = await self.generate_practise_reply(student_text)
        expected_practise = teacher_info.get("new_practise", None)
        if expected_practise:
            self.current_exercise = expected_practise
            try:
                expected_messages = parse_pinyin(expected_practise)
            except Exception as e:
                logger.error(f"error: {e} expected_practise: {expected_practise}")
                return 
            audio_bytes = await self.tts.generate_audio(expected_practise, platform=platform)
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"], expected_messages=expected_messages, audio_bytes=audio_bytes)
        else:
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])