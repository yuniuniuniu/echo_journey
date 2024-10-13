from echo_journey.data.whole_context import WholeContext
import os

class SceneGenerateBot():
    def __init__(self):
        self.context = WholeContext.generate_context_by_json(os.getenv("SceneGenerateBotPath"), "scene_generate_bot")
        
    async def generate_scene_by(self, last_teacher_msg, user_msg):
        format_dict = {}
        format_dict["TEACHER"] = last_teacher_msg
        format_dict["STUDENT"] = user_msg
        self.context.add_user_msg_to_cur({"role": "user", "content": 
            self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)})
        scene_info = await self.context.execute()
        return scene_info
        