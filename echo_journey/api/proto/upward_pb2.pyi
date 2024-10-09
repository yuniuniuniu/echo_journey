from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UpwardMessageType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[UpwardMessageType]
    STUDENT_MESSAGE: _ClassVar[UpwardMessageType]
    AUDIO_MESSAGE: _ClassVar[UpwardMessageType]
UNKNOWN: UpwardMessageType
STUDENT_MESSAGE: UpwardMessageType
AUDIO_MESSAGE: UpwardMessageType

class UpwardMessage(_message.Message):
    __slots__ = ("type", "payload")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    type: UpwardMessageType
    payload: bytes
    def __init__(self, type: _Optional[_Union[UpwardMessageType, str]] = ..., payload: _Optional[bytes] = ...) -> None: ...

class StudentMessage(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class AudioMessage(_message.Message):
    __slots__ = ("expected_sentence", "audio_data")
    EXPECTED_SENTENCE_FIELD_NUMBER: _ClassVar[int]
    AUDIO_DATA_FIELD_NUMBER: _ClassVar[int]
    expected_sentence: str
    audio_data: bytes
    def __init__(self, expected_sentence: _Optional[str] = ..., audio_data: _Optional[bytes] = ...) -> None: ...
