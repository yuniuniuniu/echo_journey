import yaml
from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.upward_pb2 import StudentMessage
from echo_journey.common.utils import parse_pinyin
from echo_journey.data.assistant_content import AssistantContent
from echo_journey.data.assistant_meta import AssistantMeta
from echo_journey.data.whole_context import WholeContext

class TalkPractiseService:
    def __init__(self, session_id, ws_msg_handler):
        self.session_id = session_id
        self.ws_msg_handler: DownwardProtocolHandler = ws_msg_handler
        self.main_chat_context = None
        
    async def initialize(self):
        content = yaml.safe_load(open("echo_journey/services/meta/talk_practise.yaml", "r"))
        talk_assistant = AssistantMeta(assistant_name="talk_assistant", content=AssistantContent(content=content))
        self.main_chat_context = WholeContext.build_from(assistant_meta=talk_assistant)
        treating_message = "那你今天有什么想聊的话题呢？可以跟我说说，如果没什么的想法的话我就给你推荐几个日常的"
        self.main_chat_context.add_assistant_msg_to_cur({"role": "assistant", "content": treating_message})
        await self.ws_msg_handler.send_tutor_message(text=treating_message)
        
    async def process_student_message(self, student_message: StudentMessage):
        student_text = student_message.text
        self.main_chat_context.add_assistant_msg_to_cur({"role": "user", "content": student_text})
        # 这里返回文字及需要练习的拼音
        await self.ws_msg_handler.send_tutor_message(text="来，你再读一下")

    
    async def process_audio_message(self, audio_message):
        expected_messages = parse_pinyin("咖啡")  
        messages = parse_pinyin("啊微")
        suggestions = """
        “咖” 应该是发“kā”的音，但你说成了“啊”，这个可能是因为你的嘴巴没有完全张开，或者舌头的位置不对。
        “啡” 应该是发“fēi”的音，但你发出了“微”的音，可能是因为你没有正确地用上下门齿稍微咬住下嘴唇来发音。
        读咖的时候张大嘴巴，像在说“啊”的时候。舌尖靠近上颚，气流从喉咙冲出。对着镜子，先发“kā”，然后慢慢说，把“kā”音发得清晰有力。
        读啡的时候，放松嘴唇，上门齿稍微咬住下嘴唇。气流从牙齿和嘴唇间流出。对着镜子，先发“fēi”，注意上门齿与下嘴唇的接触。
        """
        await self.ws_msg_handler.send_correct_message(suggestions=suggestions, expected_messages=expected_messages, msgs=messages)
