# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: downward.proto
# Protobuf Python Version: 5.28.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0e\x64ownward.proto\x12\x15\x65\x63ho_journey.downward\"\\\n\x0f\x44ownwardMessage\x12\x38\n\x04type\x18\x01 \x01(\x0e\x32*.echo_journey.downward.DownwardMessageType\x12\x0f\n\x07payload\x18\x02 \x01(\x0c\"b\n\x0cTutorMessage\x12\x0c\n\x04text\x18\x01 \x01(\t\x12\x44\n\x11\x65xpected_messages\x18\x02 \x03(\x0b\x32).echo_journey.downward.WordCorrectMessage\"k\n\x12WordCorrectMessage\x12\x0c\n\x04word\x18\x01 \x01(\t\x12\x19\n\x11initial_consonant\x18\x02 \x01(\t\x12\x0e\n\x06vowels\x18\x03 \x01(\t\x12\x0c\n\x04tone\x18\x04 \x01(\x05\x12\x0e\n\x06pinyin\x18\x05 \x01(\t\"\xb0\x01\n\x16SentenceCorrectMessage\x12\x44\n\x11\x65xpected_messages\x18\x01 \x03(\x0b\x32).echo_journey.downward.WordCorrectMessage\x12;\n\x08messages\x18\x02 \x03(\x0b\x32).echo_journey.downward.WordCorrectMessage\x12\x13\n\x0bsuggestions\x18\x03 \x01(\t*m\n\x13\x44ownwardMessageType\x12\x0b\n\x07UNKNOWN\x10\x00\x12\x11\n\rTUTOR_MESSAGE\x10\x01\x12\x18\n\x14WORD_CORRECT_MESSAGE\x10\x02\x12\x1c\n\x18SENTENCE_CORRECT_MESSAGE\x10\x03\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'downward_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_DOWNWARDMESSAGETYPE']._serialized_start=523
  _globals['_DOWNWARDMESSAGETYPE']._serialized_end=632
  _globals['_DOWNWARDMESSAGE']._serialized_start=41
  _globals['_DOWNWARDMESSAGE']._serialized_end=133
  _globals['_TUTORMESSAGE']._serialized_start=135
  _globals['_TUTORMESSAGE']._serialized_end=233
  _globals['_WORDCORRECTMESSAGE']._serialized_start=235
  _globals['_WORDCORRECTMESSAGE']._serialized_end=342
  _globals['_SENTENCECORRECTMESSAGE']._serialized_start=345
  _globals['_SENTENCECORRECTMESSAGE']._serialized_end=521
# @@protoc_insertion_point(module_scope)
