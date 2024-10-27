from pypinyin import pinyin, Style
import jieba

from echo_journey.api.proto.downward_pb2 import WordCorrectMessage


class PinyinParser:
    @classmethod
    def _get_pinyin_with_context(cls, words):
        pinyin_list = []
        pretty_pinyin_list = []
        shengmu_list = []
        for word in words:
            pinyin_word = pinyin(word, style=Style.TONE3, heteronym=True)
            pretty_pinyin_word = pinyin(word, style=Style.TONE, heteronym=True)
            shengmu = pinyin(word, style=Style.INITIALS, heteronym=True)
            
            for idx, chars in enumerate(pinyin_word):
                if len(chars) > 1:
                    pinyin_list.append(cls._disambiguate(word, idx, chars))
                else:
                    pinyin_list.append(chars[0])
            for idx, chars in enumerate(pretty_pinyin_word):
                if len(chars) > 1:
                    pretty_pinyin_list.append(cls._disambiguate(word, idx, chars))
                else:
                    pretty_pinyin_list.append(chars[0])
            for idx, chars in enumerate(shengmu):
                if len(chars) > 1:
                    shengmu_list.append(cls._disambiguate(word, idx, chars))
                else:
                    shengmu_list.append(chars[0])

        return pinyin_list, pretty_pinyin_list, shengmu_list

    @classmethod
    def _disambiguate(cls, word, idx, candidates):
        return candidates[0]
    
    @classmethod
    def _parse_yunmu_from(cls, pinyin_wo_tone, shengmu):
        if not shengmu and len(pinyin_wo_tone) > 0 and pinyin_wo_tone[0] in {'y', 'w'}:
            yunmu = pinyin_wo_tone[1:]       
        else:
            yunmu = pinyin_wo_tone[len(shengmu):]
            
        if len(pinyin_wo_tone) > 0 and pinyin_wo_tone[0] in {'j', 'q', 'x', 'y'} and yunmu == "u":
            yunmu = "ü"
        
        if yunmu == "v":
            yunmu = "ü"
        
        if yunmu == "ue":
            yunmu = "üe"
        return yunmu
    
    @classmethod
    def _deal_with_special_word(cls, word, text):
        if word == "重" and "复" in text:
            return WordCorrectMessage(word="重", initial_consonant="ch", vowels="ong", tone=2, pinyin="chóng")
        elif word == "地" and text[-1] != "地":
            return WordCorrectMessage(word="地", initial_consonant="d", vowels="e", tone=5, pinyin="de")
        elif word == "还" and text[-1] == "还":
            return WordCorrectMessage(word="还", initial_consonant="h", vowels="uan", tone=2, pinyin="huán")
        elif word == "还" and ("还钱" in text or "还东西" in text):
            return WordCorrectMessage(word="还", initial_consonant="h", vowels="uan", tone=2, pinyin="huán")
        else:
            return None    

    @classmethod
    def parse_pinyin(cls, text):
        result = []
        try:
            text = text.replace(",", "").replace("，", "").replace("。", "").replace(".", "").replace("？", "").replace("！", "").replace("；", "").replace("：", "").replace("、", "").replace(" ", "").replace("\n", "").replace("\t", "").replace("\r", "").replace("“", "").replace("”", "").replace("‘", "").replace("’", "").replace("（", "").replace("）", "").replace("《", "").replace("》", "").replace("【", "").replace("】", "").replace("—", "").replace("…", "").replace("·", "").replace("「", "").replace("」", "").replace("『", "").replace("』", "").replace("〈", "").replace("〉", "")
        except Exception as e:
            return result
        
        words = jieba.lcut(text)
        pinyin_with_tone_list, pretty_pinyin_list, shengmu_list = cls._get_pinyin_with_context(words)
        for i, pinyin_with_tone in enumerate(pinyin_with_tone_list):
            word = text[i]
            special_word = cls._deal_with_special_word(word, text)
            if special_word:
                result.append(special_word)
                continue
   
            pretty_pinyin = pretty_pinyin_list[i]
            shengmu = shengmu_list[i]
            if len(pinyin_with_tone) > 0 and pinyin_with_tone[-1].isdigit():
                tone = pinyin_with_tone[-1]
                pinyin_wo_tone = pinyin_with_tone[:-1]
            else:
                tone = '5'
                pinyin_wo_tone = pinyin_with_tone
            yunmu = cls._parse_yunmu_from(pinyin_wo_tone, shengmu)
            result.append(WordCorrectMessage(word=word, initial_consonant=shengmu, vowels=yunmu, tone=int(tone), pinyin=pretty_pinyin))

        return result