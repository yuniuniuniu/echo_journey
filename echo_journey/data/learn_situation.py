import json
import os
from echo_journey.common.utils import device_id_var
from datetime import datetime

class LearnSituation:
    def __init__(self):
        device_id = device_id_var.get()
        current_datetime = datetime.now()
        current_date_str = current_datetime.strftime('%Y-%m-%d')
        self.save_path = f"user_info/{device_id}/learn_situation/{current_date_str}.json"
        if os.path.exists(self.save_path):
            with open(self.save_path, 'r') as f:
                self.scene_2_word_2_wrong_pron_list = json.load(f)
        else:
            self.scene_2_word_2_wrong_pron_list = {}   
    
    def update(self, scene, word, pron):
        self.scene_2_word_2_wrong_pron_list[scene] = self.scene_2_word_2_wrong_pron_list.get(scene, {})
        self.scene_2_word_2_wrong_pron_list[scene][word] = self.scene_2_word_2_wrong_pron_list[scene].get(word, [])
        self.scene_2_word_2_wrong_pron_list[scene][word].append(pron)
        
    def save(self):
        directory = os.path.dirname(self.save_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(self.save_path, 'w') as f:
            json.dump(self.scene_2_word_2_wrong_pron_list, f, ensure_ascii=False, indent=4)
    