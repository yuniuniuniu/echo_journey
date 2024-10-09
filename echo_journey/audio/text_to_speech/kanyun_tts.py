import asyncio
import json
import logging
import re
import string

from py_yuntts_client import NacosClient, TtsRequest

from echo_journey.api.metric_collector import MetricCollector
from echo_journey.audio.text_to_speech.base import (
    TextAudioTimeline,
    TextToSpeech,
)
from echo_journey.common.utils import Singleton, timed, get_timer

logger = logging.getLogger(__name__)

timer = get_timer()
metric_collector: MetricCollector = MetricCollector.get_instance()


class KanyunTTS(Singleton, TextToSpeech):
    def __init__(self):
        super().__init__()
        logger.info("Initializing [KANYUN Text To Speech] voices...")
        self.client = NacosClient(service_name="apeman-yuntts")

    @timed
    async def generate_audio(self, text, language="zh-CN", speaker=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.tts_sync, text, speaker)

    def _add_punctuation_if_disappear_after_tts(self, text, time_audio_timeline_list):
        if not time_audio_timeline_list:
            return
        after_tts_text_list = [
            time_audio_timeline.text for time_audio_timeline in time_audio_timeline_list
        ]
        after_tts_text = "".join(after_tts_text_list)
        if (
            text[-1] in {".", "?", "!", "，", "。", "？", "！", ","}
            and text[-1] != after_tts_text[-1]
        ):
            time_audio_timeline_list[-1].text += text[-1]
        return time_audio_timeline_list

    def tts_sync(self, text, speaker="math-tutor-man-0926"):
        speaker = speaker or "math-tutor-man-0926"
        timer.start("KANYUN_TTS")
        tts_request = TtsRequest(
            text=text,
            encoding="mp3",
            speaker=speaker,
            app_id="math-tutor",
            user_id="math-tutor-lab",
            with_timestamp=True,
        )
        tts_response = self.client.tts(tts_request)
        metric_collector.observe_time_to_tts()
        time_audio_timeline_list = self._get_text_audio_timeline_list(
            tts_response.timestamp
        )
        time_audio_timeline_list = self._add_punctuation_if_disappear_after_tts(
            text, time_audio_timeline_list
        )
        return bytes.fromhex(tts_response.audio.audio_bytes), time_audio_timeline_list

    def _get_text_audio_timeline_list(self, json_str):
        try:
            time_stamp_json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse json: {json_str}")
            return
        time_audio_timeline_list = []
        for word_and_time_info in time_stamp_json_data["words"]:
            word = word_and_time_info["word"]
            if word == "#2" or word == "#3":
                word = ""
            start_time = word_and_time_info["start_time"]
            end_time = word_and_time_info["end_time"]
            time_audio_timeline_list.append(
                TextAudioTimeline(word, start_time, end_time)
            )

        time_audio_timeline_list = self.fix_tts_space(time_audio_timeline_list)
        return time_audio_timeline_list

    @staticmethod
    def fix_tts_space(time_audio_timeline_list):
        def is_english_alpha(char):
            return bool(re.match(r"^[A-Za-z]$", char))

        # 解决英文单词组合起来没有空格的问题
        # 1. 当前最后一个字符是字母，后面第一个字符不是标点
        # 2. 当前最后一个字符不是字母，后面第一个字符是字母
        for i in range(len(time_audio_timeline_list) - 1):
            current_text = time_audio_timeline_list[i].text
            next_text = time_audio_timeline_list[i + 1].text
            if len(current_text) > 0 and is_english_alpha(current_text[-1]):
                if len(next_text) > 0 and next_text[0] not in string.punctuation:
                    time_audio_timeline_list[i].text += " "
            else:
                if len(next_text) > 0 and is_english_alpha(next_text[0]):
                    time_audio_timeline_list[i].text += " "
        return time_audio_timeline_list
