from echo_journey.api.proto.upward_pb2 import (
    AudioMessage,
    StudentMessage,
    UpwardMessageType,
    UpwardMessage,
)

message_type_to_class = {
    UpwardMessageType.STUDENT_MESSAGE: StudentMessage,
    UpwardMessageType.AUDIO_MESSAGE: AudioMessage,
}

class_to_message_type = {v: k for k, v in message_type_to_class.items()}


def wrap_upward_message(message):
    message_type = class_to_message_type.get(type(message))
    if message_type is None:
        raise ValueError(f"Unknown payload type: {type(message).__name__}")

    upward_message = UpwardMessage()
    upward_message.type = message_type
    upward_message.payload = message.SerializeToString()

    return upward_message


def unwrap_upward_message_from_bytes(upward_message_bytes):
    upward_message = UpwardMessage()
    upward_message.ParseFromString(upward_message_bytes)
    return unwrap_upward_message(upward_message)


def unwrap_upward_message(upward_message):
    message_class = message_type_to_class.get(upward_message.type)
    if message_class is None:
        raise ValueError(f"Unknown message type: {upward_message.type}")

    message_instance = message_class()
    message_instance.ParseFromString(upward_message.payload)
    return message_instance
