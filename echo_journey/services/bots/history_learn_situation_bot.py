from echo_journey.data.learn_situation import HistoryLearnSituation
from echo_journey.data.whole_context import WholeContext
import os
from dotenv import find_dotenv, load_dotenv
import json
_ = load_dotenv(find_dotenv())

class HistoryLearnSituationBot():
    def __init__(self):
        self.context = WholeContext.generate_context_by_json(os.getenv("HistoryLearnSituationBotPath"), "scene_generate_bot")
        finals_pron_path = os.getenv("FinalsPronPath")
        with open(finals_pron_path, 'r') as f:
            self.finals_pron = json.load(f)
        initials_pron_path = os.getenv("InitialsPronPath")
        with open(initials_pron_path, 'r') as f:
            self.initials_pron = json.load(f)
        
    async def generate_treating_msg(self):
        data_info_in_str = HistoryLearnSituation().build_info()
        try:
            miss_related_set = HistoryLearnSituation().build_miss_related_set()
        except Exception as e:
            miss_related_set = set()
        self._person_bot_by(miss_related_set)
        user_msg = f"学生昨日学习情况: {data_info_in_str}"
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        treating_and_analysis_reult = await self.context.execute()
        return treating_and_analysis_reult["teacher"]       
    
    def _person_bot_by(self, miss_related_set: set):
        initials_str = ""
        finals_str = ""
            
        for miss_related in miss_related_set:
            if miss_related in self.initials_pron:
                miss_str = self.initials_pron[miss_related]
                initials_str += f"{miss_related}: {miss_str}\n"
            if miss_related in self.finals_pron:
                miss_str = self.finals_pron[miss_related]
                finals_str += f"{miss_related}: {miss_str}\n"

        if not initials_str:
            initials_str = "暂时未发现学生的声母错误"
        if not finals_str:
            finals_str = "暂时未发现学生的韵母错误"
        self.context.cur_visible_assistant.content.system_prompt =  self.context.cur_visible_assistant.content.system_prompt.replace(r"""{initials}""", initials_str)   
        self.context.cur_visible_assistant.content.system_prompt =  self.context.cur_visible_assistant.content.system_prompt.replace(r"""{finals}""", finals_str)  