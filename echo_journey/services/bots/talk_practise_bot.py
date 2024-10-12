from echo_journey.common.utils import parse_pinyin
from echo_journey.data.whole_context import WholeContext
from echo_journey.services.bots.practise_progress import PractiseProgress
import os

class TalkPractiseBot():
    def __init__(self, practise_progress, ws_msg_handler):
        self.context = WholeContext.generate_context_by_yaml(os.getenv("TalkPractiseBotPath"), "talk_practise_bot")
        self.practise_progress: PractiseProgress = practise_progress
        self.ws_msg_handler = ws_msg_handler
        
    async def send_treating_msg(self):
        treating_message = "那你今天有什么想聊的话题呢？可以跟我说说，如果没什么的想法的话我就给你推荐几个日常的呀"
        self.context.add_assistant_msg_to_cur({"role": "assistant", "content": treating_message})
        await self.ws_msg_handler.send_tutor_message(text=treating_message)
        
    async def send_end_class_msg(self):
        self.talk_practise_bot.add_user_msg_to_cur({"role": "user", "content": "这个场景的练习结束"})
        teacher_info = await self.context.execute()
        await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])
    
    async def generate_practise_reply(self, student_status, student_text):
        format_dict = {}
        format_dict["PLAN"] = self.practise_progress.get_cur_practise_sentence()
        format_dict["HISTORY_PRACTISE"] = self.practise_progress.get_history_student_practise()
        format_dict["CURRENT_PRACTISE"] = self.practise_progress.get_current_practise()
        format_dict["STUDENT_STATUS"] = student_status
        format_dict["STUDENT"] = student_text
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        teacher_info = await self.context.execute()
        return teacher_info
        
    async def send_practise_msg(self, student_status, student_text):
        teacher_info = await self.generate_practise_reply(student_status, student_text)
        expected_practise = self.practise_progress.get_current_practise()
        expected_messages = parse_pinyin(expected_practise)
        await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"], expected_messages=expected_messages)
        
    async def send_chat_msg(self, user_msg):
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        teacher_info = await self.context.execute()
        await self.ws_msg_handler.send_tutor_message(text=teacher_info["teacher"])