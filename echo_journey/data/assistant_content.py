import yaml

class AssistantContent:
    def __init__(self, content: dict):
        self.system_prompt = content.get("system_prompt", "")
        self.user_prompt_prefix = content.get("user_prompt_prefix", "")
        self.prefix_messages = content.get("prefix_messages", "[]")
        self.commit_last_n_rounds = content.get("commit_last_n_rounds", False)
        self.keep_round_nums = content.get("keep_round_nums", 0)
        self.json_mode = content.get("json_mode", False)

    def is_empty(self):
        return (
            not self.system_prompt
            and not self.user_prompt_prefix
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
            self.prefix_messages_in_list = []

        if not self.prefix_messages_in_list:
            self.prefix_messages_in_list = []