DEFAULT_PREPROCESS_FUNC = """from one_on_one_assistant.data.assistant_meta import AssistantMeta
from one_on_one_assistant.data.whole_context import WholeContext
import copy

def preprocess_func(cur_round_user_msg_info: dict, assistant_id_2_whole_context, cur_node_id):
    for assistant_id, whole_context in assistant_id_2_whole_context.items():
        if not assistant_id.startswith(cur_node_id):
            continue
        cur_user_msg = copy.deepcopy(cur_round_user_msg_info)
        cur_user_msg["content"] = (
            whole_context.cur_visible_assistant.content.user_prompt_prefix
            + cur_round_user_msg_info["raw_content"]
        )
        whole_context.add_user_msg_to_cur(cur_user_msg)

preprocess_func(cur_round_user_msg_info, assistant_id_2_whole_context, cur_node_id)"""


class RawNode:
    def __init__(self):
        self.invalid: bool = False
        self.node_info: str = ""
        self.preprocess_func: str = DEFAULT_PREPROCESS_FUNC
        self.postprocess_func: str = ""
        self.id = None

    def from_dict(self, raw_node_dict: dict):
        self.invalid = raw_node_dict["invalid"]
        self.node_info = raw_node_dict["node_info"]
        self.preprocess_func = (
            raw_node_dict["preprocess_func"]
            if raw_node_dict["preprocess_func"]
            else DEFAULT_PREPROCESS_FUNC
        )
        self.postprocess_func = raw_node_dict["postprocess_func"]
        self.id = raw_node_dict.get("id", None)
