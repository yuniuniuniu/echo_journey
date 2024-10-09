from echo_journey.api.downward_protocol_handler import DownwardProtocolHandler
from echo_journey.api.proto.downward_pb2 import TutorMessage, WordCorrectMessage
from echo_journey.common.utils import parse_pinyin


class TalkPractiseService:
    def __init__(self, session_id, ws_msg_handler):
        self.session_id = session_id
        self.ws_msg_handler: DownwardProtocolHandler = ws_msg_handler
        
    async def initialize(self):
        expected_messages = parse_pinyin("咖啡")  
        await self.ws_msg_handler.send_tutor_message(text="我们一起来练习咖啡这个单词吧", expected_messages=expected_messages)
        
    async def process_student_message(self, student_message):
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
