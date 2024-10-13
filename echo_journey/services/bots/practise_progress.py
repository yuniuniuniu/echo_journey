from enum import Enum
import logging


logger = logging.getLogger(__name__)


class PractiseStatus(Enum):
    NOTSTART = 1
    WORD = 2
    SENTENCE = 3

class PractiseProgress:
    def __init__(self):
        self.current_sentence_round = None
        self.current_word_round = None
        self.scene = None
        self.sentences_list = None
        self.current_status = None
        self.current_practise = None
            
    def init_by_content(self, content: dict):
        self.current_sentence_round = 0
        self.current_word_round = 0
        self.scene = content.get("当前场景", None)
        logger.info(f"current scene: {self.scene}")
        self.sentences_list = [content.get("短句1", []), content.get("短句2", []), content.get("短句3", [])]
        logger.info(f"sentences list: {self.sentences_list}")
        if self.scene:
            self.current_status = PractiseStatus.WORD
            self.current_practise = self.sentences_list[self.current_sentence_round][self.current_word_round]
        else:
            self.current_status = PractiseStatus.NOTSTART
            self.current_practise = None
            
    def get_next_practise(self):
        if self.current_status == PractiseStatus.SENTENCE:
            self.current_sentence_round += 1
            self.current_word_round = 0
        elif self.current_status == PractiseStatus.WORD:
            if self.current_word_round < len(self.sentences_list[self.current_sentence_round]) - 1:
                self.current_word_round += 1
            else:
                self.current_status = PractiseStatus.SENTENCE
                self.current_practise = ",".join(self.sentences_list[self.current_sentence_round])
                return self.current_practise

        if not self.is_end():
            self.current_practise = self.sentences_list[self.current_sentence_round][self.current_word_round]
        else:
            self.current_practise = None
        return self.current_practise
    
    def get_current_practise(self):
        return self.current_practise if self.current_practise else "无"
    
    def get_scene(self):
        return self.scene if self.scene else "尚未确定"
    
    def get_plan(self):
        if not self.sentences_list:
            return "无"
        result = []
        for sentence in self.sentences_list:
            result.extend(sentence)
        return ",".join(result)
    
    def get_history_student_practise(self):
        if not self.sentences_list:
            return "无"
        result = []
        sentences =  self.sentences_list[:self.current_sentence_round]
        for sentence in sentences:
            result.extend(sentence)
        result.extend(self.sentences_list[self.current_sentence_round][:self.current_word_round])
        return ",".join(result)
    
    def get_cur_practise_word(self):
        return self.sentences_list[self.current_sentence_round][self.current_word_round]
    
    def get_cur_practise_sentence(self):
        if not self.sentences_list:
            return "尚未制定"
        return ",".join(self.sentences_list[self.current_sentence_round])
            
    def is_end(self):
        return self.current_sentence_round >= len(self.sentences_list)