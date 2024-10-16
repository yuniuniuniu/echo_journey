import json
import os

from pypinyin import Style, pinyin
from echo_journey.audio.text_to_speech.kanyun_tts import KanyunTTS
from echo_journey.common.utils import chinese_to_pinyin, device_id_var, parse_pinyin
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
            
    @classmethod
    def read_from(self, path):
        learn_situation = LearnSituation()
        learn_situation.save_path = path
        if os.path.exists(learn_situation.save_path):
            with open(learn_situation.save_path, 'r') as f:
                learn_situation.scene_2_word_2_wrong_pron_list = json.load(f)
        else:
            learn_situation.scene_2_word_2_wrong_pron_list = {}
        return learn_situation
    
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
    

class HistoryLearnSituation:
    def __init__(self):
        device_id = device_id_var.get()
        storage_dir = f"user_info/{device_id}/learn_situation"
        self.data: list[LearnSituation] = []
        self.tts: KanyunTTS = KanyunTTS.get_instance()
        for root, dirs, files in os.walk(storage_dir):
            for file in files:
                if file.endswith(".json"):
                    with open(f"{storage_dir}/{file}", 'r') as f:
                        learn_situation = LearnSituation.read_from(f"{storage_dir}/{file}")
                        self.data.append(learn_situation)
                        
    def build_wrong_pronunciation_book(self, platform):
        result = {"initials": {}, "finals": {}}
        for learn_situation in self.data:
            for _, word_2_wrong_pron_list in learn_situation.scene_2_word_2_wrong_pron_list.items():
                for word in word_2_wrong_pron_list.keys():
                    word_msg_list = parse_pinyin(word)
                    audio_bytes = self.tts.generate_audio(word, platform=platform)
                    for word_msg in word_msg_list:
                        if word_msg.initial_consonant:
                            if word_msg.initial_consonant not in result["initials"]:
                                result["initials"][word_msg.initial_consonant] = []
                            result["initials"][word_msg.initial_consonant].append([word_msg_list, audio_bytes])
                        if word_msg.vowels:
                            if word_msg.vowels not in result["finals"]:
                                result["finals"][word_msg.vowels] = []
                            result["finals"][word_msg.vowels].append([word_msg_list, audio_bytes])
        return result
    
    def build_unfamilier_finals_and_initials(self):
        result = {"initials": {}, "finals": {}}
        if not self.data:
            return result
        else:
            latest_learn_situation = self.data[-1]
            for _, word_2_wrong_pron_list in latest_learn_situation.scene_2_word_2_wrong_pron_list.items():
                for word in word_2_wrong_pron_list.keys():
                    word_msg_list = parse_pinyin(word)
                    for word_msg in word_msg_list:
                        if word_msg.initial_consonant:
                            if word_msg.initial_consonant not in result["initials"]:
                                result["initials"][word_msg.initial_consonant] = 0
                            result["initials"][word_msg.initial_consonant] += 1
                        if word_msg.vowels:
                            if word_msg.vowels not in result["finals"]:
                                result["finals"][word_msg.vowels] = 0
                            result["finals"][word_msg.vowels] += 1
            return result
                        
    def build_info(self):
        result = ""
        # 学生错误把XXX读成了YYY
        result_dict = {}
        if not self.data:
            return "暂无学习情况"

        for scene, word_2_wrong_pron_list in self.data[-1].scene_2_word_2_wrong_pron_list.items():
            for word, wrong_pron_list in word_2_wrong_pron_list.items():
                if word not in result_dict:
                    result_dict[word] = set()
                for wrong_pron in wrong_pron_list:
                    result_dict[word].add(wrong_pron)
        
        error_initial_dict = {}
        error_final_dict = {}

        def is_legal(text):
            for c in text:
                if "." in c or "。" in c or "，" in c or "!" in "c" or "?" in c:
                    return False
                
            return True
        
        for word, wrong_pron_set in result_dict.items():
            for wron_pron in wrong_pron_set:
                if is_legal(wron_pron):
                    true_initials = pinyin(word, style=Style.INITIALS)
                    wrong_initials = pinyin(wron_pron, style=Style.INITIALS)
                    for index, initials in enumerate(true_initials):
                        if index < len(wrong_initials) and initials[0] != wrong_initials[index][0]:
                            if initials[0] not in error_initial_dict:
                                error_initial_dict[initials[0]] = []
                            error_initial_dict[initials[0]].append(wrong_initials[index][0])
                    true_finals = pinyin(word, style=Style.FINALS)
                    wrong_finals = pinyin(wron_pron, style=Style.FINALS)
                    for index, finals in enumerate(true_finals):
                        if index < len(wrong_finals) and finals[0] != wrong_finals[index][0]:
                            if finals[0] not in error_final_dict:
                                error_final_dict[finals[0]] = set()
                            error_final_dict[finals[0]].add(wrong_finals[index][0])
                            print(f"finals: {finals} wrong_finals: {wrong_finals[index]} word: {word} wrong_pron: {wron_pron}")
        
        def is_empty_list(input_list):
            for item in input_list:
                if item:
                    return False
            return True
        
        for initials, wrong_initials in error_initial_dict.items():
            if wrong_initials and initials and not is_empty_list(wrong_initials):
                result += f"声母{initials}错误读成了{','.join(wrong_initials)}\n"

        for finals, wrong_finals in error_final_dict.items():
            if wrong_finals and finals and not is_empty_list(wrong_finals):
                result += f"韵母{finals}错误读成了{','.join(wrong_finals)}\n"
        
        return result