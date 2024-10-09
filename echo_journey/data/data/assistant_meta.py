from __future__ import annotations
import copy
import json
import os
import subprocess
from datetime import datetime
import sys
import traceback
from urllib.parse import urlunparse, urlparse, urlencode

from dotenv import find_dotenv, load_dotenv
import yaml

from data.data.diff_result import DiffResult
from data.utils import (
    filter_history_versions_before,
    generate_commit_infos_from,
    generate_diff_html_by_text,
    get_latest_commit_id,
    push_new_commit_with,
)

from .assistant_content import AssistantContent
from .configs import (
    _ASSISTANT_2_FEATURES,
    default_additional_args_parser,
    default_append_preset_user_msg_func,
)

# TODO: 挪到settings.py @yb
_ = load_dotenv(find_dotenv())


class AssistantMetaAtCommit:
    def __init__(self, assistant_meta, commit_id):
        self.assistant_meta = assistant_meta
        self.commit_id = commit_id

    def to_dict(self):
        return {
            "assistant_name": self.assistant_meta.assistant_name,
            "branch": self.assistant_meta.branch,
            "assistant_version": self.assistant_meta.assistant_version,
            "commit_id": self.commit_id,
        }

    def __str__(self):
        return f"{self.assistant_meta.assistant_name}-{self.assistant_meta.branch}-{self.assistant_meta.assistant_version}-{self.commit_id}"


class AssistantMeta:
    def __init__(
        self,
        assistant_name,
        branch,
        assistant_version,
        content=AssistantContent({}),
        id=None,
    ):
        self.assistant_name: str = assistant_name
        self.branch: str = branch
        self.assistant_version: str = assistant_version
        self.content: AssistantContent = content
        self.id = (
            id if id else (self.assistant_name + self.branch + self.assistant_version)
        )
        self.previous_assistant_summary = None
        self.notion_page_url = None
        if self.is_exists() and self.content.is_empty():
            self.content = self.get_content()

    def to_dict(self):
        result = {
            "assistant_name": self.assistant_name,
            "branch": self.branch,
            "assistant_version": self.assistant_version,
        }
        content = self.content.to_dict()
        result.update(content)
        return result

    def is_exists(self) -> bool:
        if not self.assistant_name or not self.branch or not self.assistant_version:
            return False
        file_path = self._path()
        if not os.path.exists(file_path):
            return False
        return True

    @classmethod
    def _assistant_dir_in_cls(cls, assistant_name: str):
        assert assistant_name
        one_on_one_teacher_store_dir = cls.assistant_meta_store_root()
        assistant_dir = one_on_one_teacher_store_dir + assistant_name + "/"
        return assistant_dir

    @classmethod
    def assistant_meta_store_root(cls):
        one_on_one_teacher_store_dir = os.environ["ONE_ON_ONE_TEACHER_STORE_DIR"]
        return one_on_one_teacher_store_dir

    def _assistant_dir(self):
        return AssistantMeta._assistant_dir_in_cls(self.assistant_name)

    def _branch_dir(self):
        assert self.branch
        assistant_branch_dir = self._assistant_dir() + self.branch + "/"
        return assistant_branch_dir

    def _new_path(self, file_name: str):
        assert file_name
        assistant_branch_dir = self._branch_dir()
        assistant_meta_path = os.path.join(assistant_branch_dir, file_name)

        return assistant_meta_path

    def _path(self):
        assistant_branch_dir = self._branch_dir()
        assistant_meta_path = os.path.join(assistant_branch_dir, self.assistant_version)

        return assistant_meta_path

    def fork(self, to_assistant_name: str, to_branch_name: str):
        origin_assistant_name = self.assistant_name
        origin_branch = self.branch
        new_assistant_version_name = f"""{self.assistant_version}_fork_from_{origin_assistant_name}.{origin_branch}"""
        self.save_as(to_assistant_name, to_branch_name, new_assistant_version_name)

    def load_history_versions(self):
        result = generate_commit_infos_from(
            self._path(), AssistantMeta.assistant_meta_store_root()
        )
        previous_assistant_summary = self.previous_assistant_summary
        while previous_assistant_summary:
            assistant = AssistantMeta(
                assistant_name=previous_assistant_summary.assistant_meta.assistant_name,
                branch=previous_assistant_summary.assistant_meta.branch,
                assistant_version=previous_assistant_summary.assistant_meta.assistant_version,
            )
            commit_id = previous_assistant_summary.commit_id
            history_versions = generate_commit_infos_from(
                assistant._path(),
                AssistantMeta.assistant_meta_store_root(),
            )

            history_versions = filter_history_versions_before(
                history_versions, commit_id
            )
            result.extend(history_versions)
            previous_assistant_summary = assistant.previous_assistant_summary

        return result

    def get_history_content_by_commit_info(self, commit_info):
        if not commit_info:
            return self.content
        commit_id = commit_info.split("-")[0]
        file_path = (
            f"assistants/{self.assistant_name}/{self.branch}/{self.assistant_version}"
        )
        command = ["git", "show", f"{commit_id}:{file_path}"]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=AssistantMeta.assistant_meta_store_root(),
        )
        if not result.stdout:
            return AssistantContent({})
        else:
            return AssistantContent(json.loads(result.stdout))

    @classmethod
    def generate_diff_text_by_content(cls, diff_content, cur_content):
        system_prompt_text_prefix = (
            "----------------------------SYSTEM PROMPT----------------------------"
        )
        prefix_messages_text_prefix = (
            "----------------------------PREFIX MESSAGES----------------------------"
        )
        cur_text = (
            system_prompt_text_prefix
            + "\n"
            + cur_content.system_prompt
            + "\n"
            + prefix_messages_text_prefix
            + "\n"
            + cur_content._prefix_messages
        )
        diff_text = (
            system_prompt_text_prefix
            + "\n"
            + diff_content.system_prompt
            + "\n"
            + prefix_messages_text_prefix
            + "\n"
            + diff_content._prefix_messages
        )
        return diff_text, cur_text

    def generate_diff_result_by(self, diff_assistant_meta: AssistantMeta, commit_info):
        diff_content = diff_assistant_meta.get_history_content_by_commit_info(
            commit_info
        )
        diff_with_text, cur_text = self.generate_diff_text_by_content(
            diff_content, self.content
        )
        diff_url, diff_text = generate_diff_html_by_text(diff_with_text, cur_text)
        diff_result = DiffResult.build_from_assistant(
            self, diff_assistant_meta, commit_info, diff_url, diff_text
        )
        return diff_result

    def gen_url(self) -> str:
        base_url = os.getenv("LAB_BOT_URL")
        parsed = urlparse(base_url)

        query_dict = {
            "_tab": "single_assitant",
            "assistant": self.assistant_name,
            "branch": self.branch,
            "version": self.assistant_version,
        }

        encoded_query = urlencode(query_dict)

        url = urlunparse(parsed._replace(query=encoded_query))
        return url

    def gen_href(self) -> str:
        return f"""<a href="{self.gen_url()}" target="_blank">打开assistant URL</a>"""

    def valid_prefix_messages(self):

        def valid_yaml_formt(string):
            try:
                yaml.safe_load(string)
            except Exception as e:
                raise Exception("YAML format error", e)

        def valid_assistant_json_format(string):
            def valid_json_format(json_str):
                try:
                    json.loads(json_str)
                except Exception as e:
                    raise Exception("JSON format error", json_str)

            chats = yaml.safe_load(string)
            for chat in chats:
                if chat["role"] == "assistant" or "assistant" in chat.get("name", ""):
                    valid_json_format(chat["content"])

        prefix_messages = self.content.prefix_messages
        if not prefix_messages:
            return
        valid_yaml_formt(prefix_messages)
        if self.content.json_mode:
            valid_assistant_json_format(prefix_messages)

    def save_additional_args_as(self, chosen_additional_args_key, additional_args):
        self.content.chosen_additional_args_key = chosen_additional_args_key
        self.content.additional_args_dict[chosen_additional_args_key] = additional_args
        self.save_as()
        return list(self.content.additional_args_dict.keys())

    def save_as(
        self,
        assistant_name: str = None,
        branch: str = None,
        new_assistant_version: str = None,
    ):
        if not assistant_name:
            assistant_name = self.assistant_name
        if not branch:
            branch = self.branch
        error_msg = None
        try:
            self.valid_prefix_messages()
        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            stack_trace_list = traceback.format_exception(exc_type, exc_value, exc_tb)
            stack_trace = "".join(stack_trace_list)
            error_msg = f"Prefix msgs 格式不规范:\n 异常类型:{exc_type} \n异常值:{exc_value} \n详细堆栈跟踪信息:{stack_trace}"
        new_file_name = new_assistant_version
        if not new_file_name:
            new_file_name = self.assistant_version
        if not new_file_name:
            current_time = datetime.now()
            new_file_name = current_time.strftime("%Y-%m-%d-%H-%M-%S") + ".json"

        if not new_file_name.endswith(".json"):
            new_file_name = new_file_name + ".json"

        assert (
            assistant_name and branch and new_file_name
        ), "assistant_name, branch, new_file_name 不能为空"
        assistant_meta_path = (
            AssistantMeta.assistant_meta_store_root()
            + assistant_name
            + os.sep
            + branch
            + os.sep
            + new_file_name
        )
        if new_file_name == self.assistant_version:
            previous_assistant_summary = self.previous_assistant_summary
        else:
            cur_commit_id = get_latest_commit_id(
                AssistantMeta.assistant_meta_store_root()
            )
            previous_assistant_summary = AssistantMetaAtCommit(self, cur_commit_id)

        save_dict = self.content.to_dict()
        save_dict.update(
            {
                "previous_assistant_summary": (
                    previous_assistant_summary.to_dict()
                    if previous_assistant_summary
                    else None
                )
            }
        )
        save_dict.update(
            {
                "notion_page_url": (
                    self.notion_page_url if self.notion_page_url else None
                ),
            }
        )
        with open(assistant_meta_path, "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    save_dict,
                    ensure_ascii=False,
                )
            )

        push_new_commit_with(
            assistant_meta_path, AssistantMeta.assistant_meta_store_root()
        )
        return new_file_name, error_msg

    def get_content(self):
        if not self.content.is_empty():
            return self.content
        if not self.is_exists():
            return AssistantContent({})
        file_path = self._path()
        with open(file_path, "r", encoding="utf-8") as f:
            read_content = f.read()
            raw_content: dict = json.loads(read_content)
            previous_assistant_summary = raw_content.get(
                "previous_assistant_summary", None
            )
            if previous_assistant_summary:
                self.previous_assistant_summary = AssistantMetaAtCommit(
                    AssistantMeta(
                        assistant_name=previous_assistant_summary["assistant_name"],
                        branch=previous_assistant_summary["branch"],
                        assistant_version=previous_assistant_summary[
                            "assistant_version"
                        ],
                    ),
                    commit_id=previous_assistant_summary["commit_id"],
                )

            notion_page_url = raw_content.get("notion_page_url", None)
            if notion_page_url:
                self.notion_page_url = notion_page_url

            self.content = AssistantContent(raw_content)
        return self.content

    def get_id(self):
        return self.id

    @classmethod
    def from_meta_dict(cls, dict: dict):
        return AssistantMeta(
            assistant_name=dict["assistant_name"],
            branch=dict["branch"],
            assistant_version=dict["assistant_version"],
        )

    @classmethod
    def load_assistant_versions_from(cls, assistant_name, branch_name):
        choices = []
        choices.append("")
        one_on_one_teacher_store_dir = cls.assistant_meta_store_root()
        branch_dir_path = (
            one_on_one_teacher_store_dir + assistant_name + "/" + branch_name
        )
        if not os.path.exists(branch_dir_path):
            os.makedirs(branch_dir_path)
        files = os.listdir(branch_dir_path)
        full_paths = [os.path.join(branch_dir_path, file) for file in files]
        sorted_files = sorted(full_paths, key=os.path.getmtime, reverse=True)
        for file in sorted_files:
            if os.path.isfile(file):
                choices.append(os.path.basename(file))
        return choices

    @classmethod
    def need_function_call(cls, assistant_name):
        functions = cls.chat_functions(assistant_name)
        return functions is not None

    @classmethod
    def chat_functions(cls, assistant_name: str):
        functions = _ASSISTANT_2_FEATURES.get(assistant_name, {}).get("functions", None)
        return functions

    @classmethod
    def parse_additional_args(cls, assistant_name, additional_args_dict_str):
        parser = _ASSISTANT_2_FEATURES[assistant_name].get(
            "additional_args_parse_fn", default_additional_args_parser
        )
        return parser(additional_args_dict_str)

    @classmethod
    def user_prompt_postfix(cls, assistant_name) -> str:
        return _ASSISTANT_2_FEATURES[assistant_name].get("user_prompt_postfix", "")

    @classmethod
    def get_begin_chat_btn_info(cls, assistant_name) -> str:
        return _ASSISTANT_2_FEATURES[assistant_name].get("begin_chat_btn", False)

    @classmethod
    def state_machine_diagram(cls, assistant_name: str):
        file_name_under_assistant_dir = _ASSISTANT_2_FEATURES[assistant_name].get(
            "state_machine_diagram", None
        )
        return (
            (cls._assistant_dir_in_cls(assistant_name) + file_name_under_assistant_dir)
            if file_name_under_assistant_dir
            else None
        )

    @classmethod
    def get_user_visible_pattern(cls, assistant_name: str) -> str:
        return _ASSISTANT_2_FEATURES[assistant_name].get(
            "user_visible_pattern", "Teacher_talk"
        )

    def get_visible_dict_from_content(self) -> dict:
        content = self.get_content()
        return content.to_dict()

    @classmethod
    def get_appendable_preset_user_msg_func(cls, assistant_name: str):
        return _ASSISTANT_2_FEATURES[assistant_name].get(
            "append_preset_user_msg_func",
            lambda whole_context: default_append_preset_user_msg_func(whole_context),
        )

    @classmethod
    def temperature_of(cls, assistant_name: str):
        return _ASSISTANT_2_FEATURES[assistant_name].get("temperature", 0)
