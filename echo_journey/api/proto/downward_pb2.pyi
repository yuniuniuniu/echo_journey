from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DownwardMessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[DownwardMessageType]
    TUTOR_MESSAGE: _ClassVar[DownwardMessageType]
    WORD_CORRECT_MESSAGE: _ClassVar[DownwardMessageType]
    SENTENCE_CORRECT_MESSAGE: _ClassVar[DownwardMessageType]
UNKNOWN: DownwardMessageType
TUTOR_MESSAGE: DownwardMessageType
WORD_CORRECT_MESSAGE: DownwardMessageType
SENTENCE_CORRECT_MESSAGE: DownwardMessageType

class DownwardMessage(_message.Message):
    __slots__ = ("type", "payload")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    type: DownwardMessageType
    payload: bytes
    def __init__(self, type: _Optional[_Union[DownwardMessageType, str]] = ..., payload: _Optional[bytes] = ...) -> None: ...

class TutorMessage(_message.Message):
    __slots__ = ("text", "expected_messages", "audio")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_MESSAGES_FIELD_NUMBER: _ClassVar[int]
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    text: str
    expected_messages: _containers.RepeatedCompositeFieldContainer[WordCorrectMessage]
    audio: bytes
    def __init__(self, text: _Optional[str] = ..., expected_messages: _Optional[_Iterable[_Union[WordCorrectMessage, _Mapping]]] = ..., audio: _Optional[bytes] = ...) -> None: ...

class WordCorrectMessage(_message.Message):
    __slots__ = ("word", "initial_consonant", "vowels", "tone", "pinyin")
    WORD_FIELD_NUMBER: _ClassVar[int]
    INITIAL_CONSONANT_FIELD_NUMBER: _ClassVar[int]
    VOWELS_FIELD_NUMBER: _ClassVar[int]
    TONE_FIELD_NUMBER: _ClassVar[int]
    PINYIN_FIELD_NUMBER: _ClassVar[int]
    word: str
    initial_consonant: str
    vowels: str
    tone: int
    pinyin: str
    def __init__(self, word: _Optional[str] = ..., initial_consonant: _Optional[str] = ..., vowels: _Optional[str] = ..., tone: _Optional[int] = ..., pinyin: _Optional[str] = ...) -> None: ...

class CorrectMp4InfoMessage(_message.Message):
    __slots__ = ("mp4_url", "text")
    MP4_URL_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    mp4_url: str
    text: str
    def __init__(self, mp4_url: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class SentenceCorrectMessage(_message.Message):
    __slots__ = ("expected_messages", "messages", "suggestions", "accuracy_score", "fluency_score", "correct_mp4_info")
    EXPECTED_MESSAGES_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    SUGGESTIONS_FIELD_NUMBER: _ClassVar[int]
    ACCURACY_SCORE_FIELD_NUMBER: _ClassVar[int]
    FLUENCY_SCORE_FIELD_NUMBER: _ClassVar[int]
    CORRECT_MP4_INFO_FIELD_NUMBER: _ClassVar[int]
    expected_messages: _containers.RepeatedCompositeFieldContainer[WordCorrectMessage]
    messages: _containers.RepeatedCompositeFieldContainer[WordCorrectMessage]
    suggestions: str
    accuracy_score: float
    fluency_score: float
    correct_mp4_info: _containers.RepeatedCompositeFieldContainer[CorrectMp4InfoMessage]
    def __init__(self, expected_messages: _Optional[_Iterable[_Union[WordCorrectMessage, _Mapping]]] = ..., messages: _Optional[_Iterable[_Union[WordCorrectMessage, _Mapping]]] = ..., suggestions: _Optional[str] = ..., accuracy_score: _Optional[float] = ..., fluency_score: _Optional[float] = ..., correct_mp4_info: _Optional[_Iterable[_Union[CorrectMp4InfoMessage, _Mapping]]] = ...) -> None: ...
