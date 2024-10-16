from echo_journey.data.learn_situation import HistoryLearnSituation
from echo_journey.data.whole_context import WholeContext
import os
from dotenv import find_dotenv, load_dotenv
_ = load_dotenv(find_dotenv())

class HistoryLearnSituationBot():
    def __init__(self):
        self.context = WholeContext.generate_context_by_json(os.getenv("HistoryLearnSituationBotPath"), "scene_generate_bot")
        
    async def generate_treating_msg(self):
        data_info_in_str = HistoryLearnSituation().build_info()
        user_msg = f"学生昨日学习情况: {data_info_in_str}"
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        treating_and_analysis_reult = await self.context.execute()
        return treating_and_analysis_reult["teacher"]        