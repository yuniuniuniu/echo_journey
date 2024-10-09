import json

from ..utils import (
    STATE_PATTERN,
    choose_state_and_trans_to_str,
    extract_state_dict_from_str,
    extract_state_key_list_from_str,
    replace_state_pattern_str_by_state,
)


def default_additional_args_parser(additional_args_dict_str):
    additional_args_dict = json.loads(additional_args_dict_str)
    return additional_args_dict


_ASSISTANT_2_FEATURES = {
    "": {},
    "诊断-讲解-口语-SHOW-HAND": {},
    "并行学生回答总结": {},
    "总结Assistant": {},
    "学生为主答题-决策树引导": {},
    "学生为主答题-归并学生解决方案": {},
    "老师为主讲解": {},
    "错误定位": {},
    "playground": {},
    "工具应用": {},
    "学生为主答题⇔老师为主讲解": {},
    "口语化表达": {},
    "学生档案": {
        "temperature": 0.5,
    },
    "sft-teacher": {},
    "sft-student": {
        "temperature": 0.5,
    },
    "sft-dolphin-student": {},
    "eval-assistant": {},
}

# TODO: 将temperature放到setting附近，然后删除该文件

ASSISTANT_NAMES = _ASSISTANT_2_FEATURES.keys()

BRANCHES = [
    "default",
    "zhouyq",
    "linjingbj",
    "chentienan",
    "chishanlin",
    "yuben",
    "zhanghuiminbj01",
    "huyuruibj",
    "lisl",
    "wangdongbj02",
    "wangshanbj01",
    "hejingbj04",
    "wangxing01",
    "yanglinbj05",
]

ORCHEST_TYPES = ["变式题讲解", "工具应用"]


def default_append_preset_user_msg_func(cur_whole_context):
    last_assistant_msg = ""
    cur_chat_history = cur_whole_context.cur_chat_history
    for _, chat_msg in enumerate(cur_chat_history):
        if chat_msg["role"] == "assistant":
            last_assistant_msg = chat_msg["content"]

    user_prompt_prefix = (
        cur_whole_context.cur_visible_assistant.content.user_prompt_prefix
    )
    chosen_state_key_list = extract_state_key_list_from_str(
        STATE_PATTERN, user_prompt_prefix
    )
    state_dict = (
        extract_state_dict_from_str(last_assistant_msg) if last_assistant_msg else {}
    )
    recycle_state_str = choose_state_and_trans_to_str(state_dict, chosen_state_key_list)
    user_prompt_prefix = replace_state_pattern_str_by_state(
        STATE_PATTERN, recycle_state_str, user_prompt_prefix
    )
    return user_prompt_prefix
