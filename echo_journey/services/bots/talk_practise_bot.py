import logging
from echo_journey.audio.text_to_speech.kanyun_tts import KanyunTTS
from echo_journey.common.utils import parse_pinyin
from echo_journey.data.whole_context import WholeContext
from echo_journey.data.practise_progress import PractiseProgress
import os
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


class TalkPractiseBot():
    def __init__(self, practise_progress, ws_msg_handler):
        self.context = WholeContext.generate_context_by_json(os.getenv("TalkPractiseBotPath"), "talk_practise_bot")
        self.practise_progress: PractiseProgress = practise_progress
        self.ws_msg_handler = ws_msg_handler
        self.tts: KanyunTTS = KanyunTTS.get_instance()
        
    async def send_treating_msg(self):
        import json
        treating_dict = json.loads(self.context.cur_visible_assistant.content.prefix_messages_in_list[0]["content"])
        await self.ws_msg_handler.send_tutor_message(text=treating_dict["teacher"])
        
    async def send_end_class_msg(self):
        self.context.add_user_msg_to_cur({"role": "user", "content": "这个场景的练习结束"})
        teacher_info = await self.context.execute()
        await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
        
    def build_input_by(self, student_status, student_text):
        format_dict = {}
        format_dict["SCENE"] = self.practise_progress.get_scene()
        format_dict["PLAN"] = self.practise_progress.get_plan()
        format_dict["CURRENT_PLAN"] = self.practise_progress.get_cur_practise_sentence()
        format_dict["HISTORY_PRACTISE"] = self.practise_progress.get_history_student_practise()
        format_dict["CURRENT_PRACTISE"] = self.practise_progress.get_current_practise()
        format_dict["STUDENT_STATUS"] = student_status
        format_dict["STUDENT"] = student_text
        logger.info(f"format_dict: {format_dict}")
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        return user_msg
    
    async def generate_practise_reply(self, student_status, student_text):
        user_msg = self.build_input_by(student_status, student_text)
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        teacher_info = await self.context.execute()
        return teacher_info
    
    def add_suggestion_to_context(self, suggestions):
        import json
        user_msg = self.build_input_by("学生的发音存在问题错误", "老师帮我纠下音吧")
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        assistant_msg = json.dumps({"skip": False, "teacher": suggestions}, ensure_ascii=False)
        self.context.add_assistant_msg_to_cur({"role": "assistant", "content": assistant_msg})
        
    async def send_practise_msg(self, student_status, student_text, platform):
        teacher_info = await self.generate_practise_reply(student_status, student_text)
        expected_practise = self.practise_progress.get_current_practise()
        if expected_practise and expected_practise != "无":
            try:
                expected_messages = parse_pinyin(expected_practise)
            except Exception as e:
                logger.error(f"error: {e} expected_practise: {expected_practise}")
                return 
            audio_bytes = await self.tts.generate_audio(expected_practise, platform=platform)
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"], expected_messages=expected_messages, audio_bytes=audio_bytes)
        else:
            await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])