from echo_journey.api.proto.downward_pb2 import (
    DownwardMessageType,
    DownwardMessage,
    SentenceCorrectMessage,
    TutorMessage,
    WordCorrectMessage,
)

message_type_to_class = {
    DownwardMessageType.TUTOR_MESSAGE: TutorMessage,
    DownwardMessageType.WORD_CORRECT_MESSAGE: WordCorrectMessage,
    DownwardMessageType.SENTENCE_CORRECT_MESSAGE: SentenceCorrectMessage

}

class_to_message_type = {v: k for k, v in message_type_to_class.items()}


def wrap_downward_message(message):
    message_type = class_to_message_type.get(type(message))
    if message_type is None:
        raise ValueError(f"Unknown payload type: {type(message).__name__}")

    downward_message = DownwardMessage()
    downward_message.type = message_type
    # 注意存在自定义的，非Protobuf的消息
    if hasattr(message, "SerializeToString"):
        downward_message.payload = message.SerializeToString()
    return downward_message


def unwrap_downward_message_from_bytes(downward_message_bytes):
    downward_message = DownwardMessage()
    downward_message.ParseFromString(downward_message_bytes)
    return unwrap_downward_message(downward_message)


def unwrap_downward_message(downward_message):
    message_class = message_type_to_class.get(downward_message.type)
    if message_class is None:
        raise ValueError(f"Unknown message type: {downward_message.type}")

    # 注意存在自定义的，非Protobuf的消息
    message_instance = message_class()
    if hasattr(message_instance, "ParseFromString"):
        message_instance.ParseFromString(downward_message.payload)
    return message_instance
