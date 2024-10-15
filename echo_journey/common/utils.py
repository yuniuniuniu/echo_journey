import asyncio
import logging
from time import perf_counter
from typing import List, Optional, Callable

from starlette.websockets import WebSocket, WebSocketState

from echo_journey.api.proto.downward_pb2 import WordCorrectMessage

import logging

import contextvars
logger = logging.getLogger(__name__)
session_id_var = contextvars.ContextVar("session_id", default="N/A")
device_id_var = contextvars.ContextVar("device_id", default="N/A")

class SessionFilter(logging.Filter):
    def filter(self, record):
        record.session_id = session_id_var.get()
        return True


class Singleton:
    _instances = {}

    @classmethod
    def get_instance(cls, *args, **kwargs):
        """Static access method."""
        if cls not in cls._instances:
            cls._instances[cls] = cls(*args, **kwargs)

        return cls._instances[cls]

    @classmethod
    def initialize(cls, *args, **kwargs):
        """Static access method."""
        if cls not in cls._instances:
            cls._instances[cls] = cls(*args, **kwargs)


class ConnectionManager(Singleton):
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Client #{id(websocket)} left the chat")
        # await self.broadcast_message(f"Client #{id(websocket)} left the chat")

    async def send_message(self, message: str, websocket: WebSocket):
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.send_text(message)

    async def broadcast_message(self, message: str):
        for connection in self.active_connections:
            if connection.application_state == WebSocketState.CONNECTED:
                await connection.send_text(message)


def get_connection_manager():
    return ConnectionManager.get_instance()


class Timer(Singleton):
    def __init__(self):
        self.start_time: dict[str, float] = {}
        self.elapsed_time: dict[str, List[float]] = {}
        self.logger = logging.getLogger("Timer")

    def start(self, id: str):
        self.start_time[id] = perf_counter()

    def get_elapsed_time_of(self, id: str):
        if id in self.start_time:
            elapsed_time = perf_counter() - self.start_time[id]
            return elapsed_time
        return None

    def log(self, id: str, callback: Optional[Callable] = None):
        if id in self.start_time:
            elapsed_time = perf_counter() - self.start_time[id]
            del self.start_time[id]
            if id in self.elapsed_time:
                self.elapsed_time[id].append(elapsed_time)
            else:
                self.elapsed_time[id] = [elapsed_time]
            if callback:
                callback()

    def report(self):
        for id, t in self.elapsed_time.items():
            self.logger.info(
                f"{id:<30s}: {sum(t)/len(t):.3f}s [{min(t):.3f}s - {max(t):.3f}s] "
                f"({len(t)} samples)"
            )

    def reset(self):
        self.start_time = {}
        self.elapsed_time = {}


def get_timer() -> Timer:
    return Timer.get_instance()


def timed(func):
    if asyncio.iscoroutinefunction(func):

        async def async_wrapper(*args, **kwargs):
            timer = get_timer()
            timer.start(func.__qualname__)
            result = await func(*args, **kwargs)
            timer.log(func.__qualname__)
            return result

        return async_wrapper
    else:

        def sync_wrapper(*args, **kwargs):
            timer = get_timer()
            timer.start(func.__qualname__)
            result = func(*args, **kwargs)
            timer.log(func.__qualname__)
            return result

        return sync_wrapper

from pypinyin import lazy_pinyin, Style, pinyin


def chinese_to_pinyin(text, style=Style.TONE, delimiter=' '):
    pinyin_list = pinyin(text, style=style)
    pinyin_str = delimiter.join([''.join(item) for item in pinyin_list])
    return pinyin_str

def parse_pinyin(text):
    result = []
    text = text.replace(",", "").replace("，", "").replace("。", "").replace(".", "").replace("？", "").replace("！", "").replace("；", "").replace("：", "").replace("、", "").replace(" ", "").replace("\n", "").replace("\t", "").replace("\r", "").replace("“", "").replace("”", "").replace("‘", "").replace("’", "").replace("（", "").replace("）", "").replace("《", "").replace("》", "").replace("【", "").replace("】", "").replace("—", "").replace("…", "").replace("·", "").replace("「", "").replace("」", "").replace("『", "").replace("』", "").replace("〈", "").replace("〉", "")
    
    pinyin_list = lazy_pinyin(text, style=Style.TONE3, neutral_tone_with_five=True)
    shengmu_list = lazy_pinyin(text, style=Style.INITIALS)   

    for i, char in enumerate(text):
        pinyin = pinyin_list[i]
        shengmu = shengmu_list[i]
        pretty_pinyin=chinese_to_pinyin(char)
        pinyin_wo_tone = chinese_to_pinyin(char, Style.NORMAL)
        
        if len(pinyin) > 0 and pinyin[-1].isdigit():
            tone = pinyin[-1]
        else:
            tone = '5'
            
        yunmu = pinyin_wo_tone[len(shengmu):]
        
        result.append(WordCorrectMessage(word=char, initial_consonant=shengmu, vowels=yunmu, tone=int(tone), pinyin=pretty_pinyin))
    return result


import uuid

def generate_uuid_from_string(input_string: str) -> uuid.UUID:
    # 使用一个固定的命名空间 (dns, url, oid, or x500) 或自定义
    namespace = uuid.NAMESPACE_DNS
    return str(uuid.uuid5(namespace, input_string))


import base64

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def encode_image_bytes(image_in_bytes: bytes):
    return base64.b64encode(image_in_bytes).decode("utf-8")