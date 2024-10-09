import yaml

from data.my_logger import LOGGER


class AssistantContent:
    def __init__(self, content: dict):
        self.system_prompt = content.get("system_prompt", "")
        self.user_prompt_prefix = content.get("user_prompt_prefix", "")
        self.additional_args = content.get("additional_args", "")
        self.task_prompt_template = content.get("task_prompt_template", "")
        self.prefix_messages = content.get("prefix_messages", "[]")
        self.commit_last_n_rounds = content.get("commit_last_n_rounds", False)
        self.keep_round_nums = content.get("keep_round_nums", 0)
        self.default_llm_name = content.get("default_llm_name", "gpt4-ptu-online")
        self.default_eval_set = content.get("default_eval_set", "")
        self.json_mode = content.get("json_mode", False)  # json_mode default is True
        self.short_system_mode = content.get("short_system_mode", False)
        self.chosen_additional_args_key = content.get("chosen_additional_args_key", "")
        self.additional_args_dict = content.get("additional_args_dict", {})

    def is_empty(self):
        return (
            not self.system_prompt
            and not self.user_prompt_prefix
            and not self.chosen_additional_args_key
            and not self.prefix_messages_in_list
        )

    @property
    def prefix_messages(self):
        return self._prefix_messages

    @prefix_messages.setter
    def prefix_messages(self, text):
        self._prefix_messages = text
        try:
            self.prefix_messages_in_list = yaml.safe_load(self.prefix_messages)
        except Exception as e:
            LOGGER.error(f"prefix_messages parse error: {e}")
            self.prefix_messages_in_list = []

        if not self.prefix_messages_in_list:
            self.prefix_messages_in_list = []

    def to_dict(self):
        return {
            "system_prompt": self.system_prompt,
            "user_prompt_prefix": self.user_prompt_prefix,
            "chosen_additional_args_key": self.chosen_additional_args_key,
            "additional_args_dict": self.additional_args_dict,
            "task_prompt_template": self.task_prompt_template,
            "prefix_messages": self.prefix_messages,
            "commit_last_n_rounds": self.commit_last_n_rounds,
            "keep_round_nums": self.keep_round_nums,
            "json_mode": self.json_mode,
            "short_system_mode": self.short_system_mode,
            "default_llm_name": self.default_llm_name,
            "default_eval_set": self.default_eval_set,
        }
