from echo_journey.data.whole_context import WholeContext

class SceneGenerateBot():
    def __init__(self):
        self.context = WholeContext.generate_context_by_yaml("echo_journey/services/bots/meta/scene_generation.yaml", "scene_generate_bot")
        
    async def generate_scene_by(self, text):
        self.context.add_user_msg_to_cur({"role": "user", "content": 
            self.context.cur_visible_assistant.content.user_prompt_prefix + text})
        scene_info = await self.context.execute()
        return scene_info
        