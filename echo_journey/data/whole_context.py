import copy
import json
import time

import tiktoken
import yaml
from echo_journey.data.llm import LLM, merge_deltas
from echo_journey.data.llm_utils import create_llm
from echo_journey.data.utils import (
    encode_image,
    encode_image_bytes,
)
from .assistant_meta import AssistantMeta
from .assistant_content import AssistantContent


class WholeContext():
    def __init__(self):
        self.cur_visible_assistant: AssistantMeta = None
        self.cur_chat_history: list[dict] = []
        self.original_messages: list[dict] = []
        self.llm = create_llm("gpt4-ptu-online")
        self.additional_args = ""

    def get_original_messages(self):
        return self.original_messages

    @classmethod
    def build_from_context_dict(cls, cur_context_dict: dict):
        cur_visible_assistant = AssistantMeta(
            assistant_name=cur_context_dict.get("assistant_name", ""),
            branch=cur_context_dict.get("branch", ""),
            assistant_version=cur_context_dict.get("assistant_version", ""),
            content=AssistantContent(cur_context_dict),
        )
        # 兼容原有notion中的context
        old_chat_history: dict = cur_context_dict.get("chat_history_of", {})
        if not old_chat_history:
            cur_chat_history = cur_context_dict.get("cur_chat_history", [])
        else:
            cur_chat_history = old_chat_history.get(
                cur_visible_assistant.assistant_name, []
            )
        return WholeContext.rebuild_from(
            cur_visible_assistant,
            cur_chat_history,
        )

    def to_dict(self):
        cur_context_dict = self.cur_visible_assistant.to_dict()
        cur_context_dict["cur_chat_history"] = self.cur_chat_history
        cur_context_dict["original_messages"] = self.original_messages
        return cur_context_dict

    def to_json(self):

        cur_context_dict = self.to_dict()
        whole_context_in_json = json.dumps(
            cur_context_dict, indent=4, ensure_ascii=False
        )
        return whole_context_in_json

    def add_user_msg_to_cur(self, user_msg_dict: dict):
        user_msg_dict["timestamp"] = round(time.time(), 3)
        if "raw_pic_paths" in user_msg_dict and user_msg_dict["raw_pic_paths"]:
            image_url_dict_list = []
            for raw_pic_path in user_msg_dict["raw_pic_paths"]:
                base64_image = encode_image(raw_pic_path)
                image_url_dict_list.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    }
                )
            user_msg_dict["content"] = [
                {"type": "text", "text": user_msg_dict["content"]}
            ] + image_url_dict_list

        if "image_in_bytes" in user_msg_dict and user_msg_dict["image_in_bytes"]:
            base64_image = encode_image_bytes(user_msg_dict["image_in_bytes"])
            print("base64_image length, ", len(base64_image))
            user_msg_dict["content"] = [
                {"type": "text", "text": user_msg_dict["content"]},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ]
        user_msg_dict["assistant_id"] = self.cur_visible_assistant.get_id()
        self.cur_chat_history.append(user_msg_dict)
        self.original_messages.append(user_msg_dict)

    def overwrite_last_assitant_msg(self, assistant_msg: str):
        self.cur_chat_history[-1]["content"] = assistant_msg
        self.original_messages[-1]["content"] = assistant_msg

    def add_assistant_msg_to_cur(self, assistant_msg_dict: dict):
        assistant_msg_dict["timestamp"] = round(time.time(), 3)
        self.cur_chat_history.append(assistant_msg_dict)
        self.original_messages.append(assistant_msg_dict)

    def get_last_msg_of(self, role):
        if not self.cur_chat_history:
            return None
        for msg in reversed(self.cur_chat_history):
            if msg["role"] == role:
                return msg["content"]
        return None

    def get_role_of_last_msg(self):
        if not self.cur_chat_history:
            return None
        return self.cur_chat_history[-1]["role"]

    def append_user_msg_to_last(self, raw_user_input: str):
        self.cur_chat_history[-1]["content"] += raw_user_input

    def rewrite_user_msg_to_last(self, user_input: str, raw_user_input: str):
        self.cur_chat_history[-1]["content"] = user_input
        self.cur_chat_history[-1]["raw_content"] = raw_user_input

    def user_visible_msgs_view_commit_full_history(self, prefix_messages_in_list):
        chat_history_with_prefix_msgs = prefix_messages_in_list + self.cur_chat_history
        return chat_history_with_prefix_msgs

    def user_visible_msgs_view_commit_last_n_rounds(self, prefix_messages_in_list):
        last_index = self.cur_visible_assistant.content.keep_round_nums * 2 + 1
        if abs(last_index) > len(self.cur_chat_history):
            last_index = len(self.cur_chat_history)
        chat_history_with_prefix_msgs = (
            prefix_messages_in_list + self.cur_chat_history[-last_index:]
        )
        return chat_history_with_prefix_msgs

    def original_msgs_view(self):
        chat_history_with_prefix_msgs = (
            self.cur_visible_assistant.content.prefix_messages_in_list
            + self.original_messages
        )
        return chat_history_with_prefix_msgs

    def format_system_and_history(self):
        system_prompt = self.cur_visible_assistant.content.system_prompt
        
        prefix_messages = self.cur_visible_assistant.content.prefix_messages
        prefix_messages_in_list = yaml.safe_load(prefix_messages)
        prefix_messages_in_list = (
            [] if not prefix_messages_in_list else prefix_messages_in_list
        )
        return system_prompt, prefix_messages_in_list

    def submittable_msgs_view(self):
        system_prompt, prefix_messages_in_list = self.format_system_and_history()
        if self.cur_visible_assistant.content.commit_last_n_rounds:
            chat_history_with_prefix_msgs = (
                self.user_visible_msgs_view_commit_last_n_rounds(
                    prefix_messages_in_list
                )
            )
        else:
            chat_history_with_prefix_msgs = (
                self.user_visible_msgs_view_commit_full_history(prefix_messages_in_list)
            )

        chat_history_with_prefix_and_system_msgs = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ] + chat_history_with_prefix_msgs

        submittable_msgs = []
        for msg in chat_history_with_prefix_and_system_msgs:
            if "name" in msg:
                submittable_msgs.append(
                    {
                        "role": msg["role"],
                        "name": msg["name"],
                        "content": msg["content"],
                    }
                )
            else:
                submittable_msgs.append(
                    {"role": msg["role"], "content": msg["content"]}
                )

        return submittable_msgs

    def clear(self):
        self.cur_chat_history.clear()
        self.original_messages.clear()

    def recover_history_from(self, messages):
        self.cur_chat_history = copy.deepcopy(messages)
        self.original_messages = copy.deepcopy(messages)

    def build_with(
        self,
        last_whole_context,
    ):
        return self.rebuild_from(
            self.cur_visible_assistant,
            last_whole_context.cur_chat_history,
            self.trace_info,
            self.llm,
        )

    @classmethod
    def rebuild_from(
        cls,
        assistant_meta: AssistantMeta,
        chat_history: list[dict] = [],
        llm: LLM = create_llm("gpt4-ptu-online"),
        additional_args: str = None,
    ):
        result = WholeContext()
        result.cur_visible_assistant = assistant_meta
        if additional_args:
            result.additional_args = additional_args
        result.cur_chat_history = copy.deepcopy(chat_history)
        result.original_messages = copy.deepcopy(chat_history)
        result.llm = llm
        return result

    def postprocess_after_submit(self):
        pass

    def _validate_predix_messages(self):
        try:
            yaml.safe_load(self.cur_visible_assistant.content.prefix_messages)
        except Exception as e:
            raise yaml.YAMLError("prefix_messages parse error")

    async def submit(self):
        self._validate_predix_messages()
        submittable_msgs = self.submittable_msgs_view()
        async for bot_res, delta in self.bot_async(submittable_msgs):
            yield bot_res, delta
        self.postprocess_after_submit()

    async def _async_commit_to_llm(
        self, assistant_meta: AssistantMeta, messages: list[dict]
    ):
        functions = AssistantMeta.chat_functions(assistant_meta.assistant_name)
        temperature = AssistantMeta.temperature_of(assistant_meta.assistant_name)
        async for delta, is_restart_commit in self.llm.acommit(
            messages,
            functions,
            temperature,
            json_mode=assistant_meta.content.json_mode,
            short_system_mode=assistant_meta.content.short_system_mode,
        ):
            yield delta, is_restart_commit

    def split_delta_in_chars(self, delta):
        result = []
        if delta.get("content", ""):
            chars = list(delta["content"])
            for char in chars:
                new_delta_per_char = copy.deepcopy(delta)
                new_delta_per_char["content"] = char
                result.append(new_delta_per_char)
        else:
            result.append(delta)
        return result

    async def bot_async(self, submittable_msgs: list[dict]):
        teacher_pattern = AssistantMeta.get_user_visible_pattern(
            self.cur_visible_assistant.assistant_name
        )
        merged_response = {}
        assistant_res = []

        async for delta_in_token, is_restart_commit in self._async_commit_to_llm(
            self.cur_visible_assistant, submittable_msgs
        ):
            if is_restart_commit:
                merged_response = {}
                continue

            new_deltas_per_char = self.split_delta_in_chars(delta_in_token)
            for delta in new_deltas_per_char:
                merged_response = merge_deltas(merged_response, delta)
                if (
                    "content" in merged_response
                    and "role" in merged_response
                    and merged_response["role"] == "assistant"
                ):
                    yield assistant_res + [
                        {
                            "role": "assistant",
                            "content": merged_response["content"],
                        }
                    ], delta

        if "content" not in merged_response:
            merged_response["content"] = ""

        assistant_res.append(
            {
                "role": "assistant",
                "content": merged_response["content"],
                "stat": merged_response["stat"],
                "assistant_id": self.cur_visible_assistant.get_id(),
            }
        )
        yield assistant_res, {}

    def get_token_count(self, text):
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))

    async def travel_with_generator(
        self,
        cur_round_user_msg_info: dict,
        llm: LLM = None,
    ):
        self.llm = llm if llm else self.llm
        async for bot_res_list, _ in self.submit():
            yield bot_res_list
        for bot_res in bot_res_list:
            self.add_assistant_msg_to_cur(bot_res)

    async def travel_with_callback(
        self,
        cur_round_user_msg_info: dict,
        llm: LLM,
        on_new_delta: callable,
    ):
        last_bot_res = []
        bot_req = self.cur_chat_history[-1]
        self.llm = llm if llm else self.llm
        async for bot_res, delta in self.submit():
            if "content" in delta:
                await on_new_delta(self.get_id(), bot_req, bot_res, delta)
                last_bot_res = bot_res
        await on_new_delta(
            self.get_id(),
            bot_req,
            last_bot_res,
            {"content": ""},
            is_assistant_request_completed=True,
        )

    def get_visible_msgs(self, new_msgs):
        return self.get_original_messages() + new_msgs

    def get_id(self):
        return self.cur_visible_assistant.get_id()

    def __deepcopy__(self, memo):
        copied_instance = WholeContext()
        for key, value in vars(self).items():
            if key == "llm":
                copied_instance.llm = (
                    create_llm(self.llm.get_config_name()) if self.llm else None
                )
            else:
                setattr(copied_instance, key, copy.deepcopy(value, memo))
        return copied_instance
