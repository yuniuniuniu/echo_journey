import copy
from datetime import datetime
import json
import os
import subprocess
from urllib.parse import urlparse, urlencode, urlunparse

import yaml
from data.data.assistant_meta import AssistantMeta
from data.data.base_context import BaseContext
from data.data.diff_result import DiffResult
from data.data.orchestrator_edge import OrchestratorEdge
from data.data.orchestrator_node import OrchestratorNode
from data.data.trace_info import TraceInfo
from data.data.whole_context import WholeContext
from data.data.raw_edge import RawEdge
from data.data.raw_node import RawNode
from data.llm import LLM
from data.utils import (
    filter_and_sort_commit_infos,
    filter_history_versions_before,
    generate_commit_infos_from,
    generate_diff_html_by_text,
    get_latest_commit_id,
    sort_commit_infos,
)


class OrchestratorAtCommit:
    def __init__(self, orchestrator, commit_id):
        self.orchestrator = orchestrator
        self.commit_id = commit_id

    def to_dict(self):
        return {
            "orchest_type": self.orchestrator.orchest_type,
            "branch": self.orchestrator.branch,
            "name": self.orchestrator.name,
            "commit_id": self.commit_id,
        }

    def __str__(self):
        return f"{self.orchest_type}-{self.branch}-{self.name}-{self.commit_id}"


class Orchestrator(BaseContext):
    def __init__(self) -> None:
        self.raw_start_node_index: int = None
        self.orchest_type = None
        self.branch = None
        self.name = None
        self.raw_node_dict: dict[int, RawNode] = {}
        self.raw_edge_dict: dict[int, RawEdge] = {}
        self.raw_node_count: int = 0
        self.raw_edge_count: int = 0
        self.additional_args_key = ""
        self.additional_args = ""
        self.additional_args_dict = {}
        self.main_assistant_list: list[AssistantMeta] = []
        self.visible_assistants: list[AssistantMeta] = []
        self.start_node: OrchestratorNode = None
        self.id_2_node: dict[int, OrchestratorNode] = {}
        self.assistant_id_2_whole_context: dict[str, WholeContext] = {}
        self.outgoing_edges: dict[int, list[OrchestratorEdge]] = {}
        self.node_travel_history: list[int] = []
        self.previous_orchestrator_summary = None

    def get_id(self):
        return f"{self.orchest_type}-{self.branch}-{self.name}"

    def get_main_context(self) -> WholeContext:
        cur_main_assistant = None
        for node_id in reversed(self.node_travel_history):
            cur_node = self.id_2_node[node_id]
            assistant_ids_in_node = set(cur_node.assistant_id_2_whole_context.keys())
            for assistant in self.main_assistant_list:
                if assistant.get_id() in assistant_ids_in_node:
                    cur_main_assistant = assistant
                    break
        return self.assistant_id_2_whole_context[cur_main_assistant.get_id()]

    def build_with(self, another_orchestrator):
        new_orchestrator = copy.deepcopy(self)
        new_orchestrator.assistant_id_2_whole_context = copy.deepcopy(
            another_orchestrator.assistant_id_2_whole_context
        )
        return new_orchestrator

    def to_dict(self):
        if not self.main_assistant_list:
            raw_main_assistant_list = None
        else:
            raw_main_assistant_list = []
            for assistant in self.main_assistant_list:
                raw_main_assistant_list.append(
                    {
                        "assistant_name": assistant.assistant_name,
                        "branch": assistant.branch,
                        "assistant_version": assistant.assistant_version,
                    }
                )

        result = {
            "raw_start_node_index": self.raw_start_node_index,
            "raw_node_count": self.raw_node_count,
            "raw_edge_count": self.raw_edge_count,
            "raw_node": {},
            "raw_edge": {},
            "main_assistant_list": raw_main_assistant_list,
            "additional_args": self.additional_args,
            "additional_args_key": self.additional_args_key,
            "additional_args_dict": self.additional_args_dict,
        }
        for node_index, raw_node in self.raw_node_dict.items():
            result["raw_node"][node_index] = vars(raw_node)

        for edge_index, raw_edge in self.raw_edge_dict.items():
            result["raw_edge"][edge_index] = vars(raw_edge)
        for assistant_id, whole_context in self.assistant_id_2_whole_context.items():
            result[assistant_id] = whole_context.to_json()
        return result

    def to_json(self):
        result = self.to_dict()
        return json.dumps(result, ensure_ascii=False)

    @classmethod
    def _persistence(cls, value, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)

        subprocess.run(["git", "add", path], cwd=Orchestrator.store_root())
        subprocess.run(
            ["git", "commit", "-m", "--ADD: new assistant version"],
            cwd=Orchestrator.store_root(),
        )

        subprocess.run(
            ["git", "pull", "origin", "main", "--rebase"],
            cwd=Orchestrator.store_root(),
        )

        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=Orchestrator.store_root(),
        )

    def _valid(self):
        if self.raw_start_node_index is None:
            raise Exception("先手动保存刚才编辑的内容，然后刷新页面！")

    def save_as(
        self, orchest_type: str = None, branch: str = None, new_file_name: str = None
    ):
        if not orchest_type:
            orchest_type = self.orchest_type
        if not branch:
            branch = self.branch
        if not new_file_name:
            new_file_name = self.name

        if not new_file_name:
            current_time = datetime.now()
            new_file_name = current_time.strftime("%Y-%m-%d-%H-%M-%S")

        if not new_file_name.endswith(".json"):
            new_file_name = new_file_name + ".json"

        save_path = (
            Orchestrator.store_root()
            + os.sep
            + orchest_type
            + os.sep
            + branch
            + os.sep
            + new_file_name
        )
        self._valid()
        save_dict = self.to_dict()
        if new_file_name == self.name:
            previous_orchestrator_summary = self.previous_orchestrator_summary
        else:
            cur_commit_id = get_latest_commit_id(self.store_root())
            previous_orchestrator_summary = OrchestratorAtCommit(self, cur_commit_id)

        save_dict.update(
            {
                "previous_orchestrator_summary": (
                    previous_orchestrator_summary.to_dict()
                    if previous_orchestrator_summary
                    else None
                )
            }
        )
        self._persistence(json.dumps(save_dict, ensure_ascii=False), save_path)

        return (
            self.load_orchestrators_from(orchest_type, branch),
            new_file_name,
        )

    def save_additional_args_as(self, orchest_type, branch, name, additional_args_key):
        self.additional_args_key = additional_args_key
        self.additional_args_dict[additional_args_key] = self.additional_args
        self.save_as(orchest_type, branch, name)
        return list(self.additional_args_dict.keys())

    def _path_in_repo(self):
        return self.orchest_type + os.sep + self.branch + os.sep + self.name

    def _path(self):
        return self.store_root() + self._path_in_repo()

    @classmethod
    def store_root(cls) -> str:
        one_on_one_teacher_store_dir = os.getenv("ORCHESTRATOR_DIR")
        return one_on_one_teacher_store_dir

    def extract_assistant_list(self):
        assistants_in_orchestration = []
        for node_index, raw_node in self.raw_node_dict.items():
            if raw_node.invalid:
                continue
            raw_node.id = node_index
            assistants_in_orchestration += OrchestratorNode.extract_assistant_list_from(
                raw_node, None
            )
        return assistants_in_orchestration

    def load_history_versions(self):
        assistants_in_orchestration = self.extract_assistant_list()
        total_commit_infos = []
        for assistant, _ in assistants_in_orchestration:
            total_commit_infos += assistant.load_history_versions()
        orchest_commit_infos = generate_commit_infos_from(
            self._path(), self.store_root()
        )
        orchest_commit_infos = sort_commit_infos(orchest_commit_infos)
        total_commit_infos += orchest_commit_infos
        total_commit_infos = list(set(total_commit_infos))
        result = total_commit_infos
        previous_orchestrator_summary = self.previous_orchestrator_summary
        while previous_orchestrator_summary:
            orchestrator = Orchestrator.build_from(
                previous_orchestrator_summary.orchestrator.orchest_type,
                previous_orchestrator_summary.orchestrator.branch,
                previous_orchestrator_summary.orchestrator.name,
            )
            commit_id = previous_orchestrator_summary.commit_id
            history_versions = generate_commit_infos_from(
                orchestrator._path(), self.store_root()
            )
            history_versions = filter_history_versions_before(
                history_versions, commit_id
            )
            result.extend(history_versions)
            previous_orchestrator_summary = orchestrator.previous_orchestrator_summary
        result = sort_commit_infos(result)
        return result

    def get_history_content_by_commit_info(self, commit_info):
        if not commit_info:
            return self.to_dict()
        commit_id = commit_info.split("-")[0]
        file_path = "orchestrators/" + self._path_in_repo()
        command = ["git", "show", f"{commit_id}:{file_path}"]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.store_root(),
        )
        orchestrator_content = json.loads(result.stdout if result.stdout else "{}")
        return orchestrator_content

    @classmethod
    def extract_text_from_content(cls, content):
        result = ""
        additional_args = content.get("additional_args", "")
        raw_start_node_index = content.get("raw_start_node_index", "")
        raw_node_count = content.get("raw_node_count", "")
        raw_edge_count = content.get("raw_edge_count", "")
        raw_node = content.get("raw_node", {})
        raw_edge = content.get("raw_edge", {})
        result += f"## raw_start_node_index \n\n {raw_start_node_index}\n\n ## raw_node_count \n\n {raw_node_count}\n\n ## raw_edge_count \n\n {raw_edge_count}\n\n ## additional_args \n\n {additional_args}\n\n"
        for key, value in raw_node.items():
            node_info = value.get("node_info", "")
            preprocess_func = value.get("preprocess_func", "")
            postprocess_func = value.get("postprocess_func", "")
            invalid = str(value.get("invalid", ""))
            result += f"## node_id: {key} \n\n node_info: {node_info}\n\n preprocess_func: {preprocess_func}\n\n postprocess_func:{postprocess_func}\n\n invalid:{invalid}\n\n"
        for key, value in raw_edge.items():
            jump_condition = value.get("jump_condition", "")
            from_node_index = str(value.get("from_node_index", ""))
            to_node_index = value.get("to_node_index", "")
            invalid = str(value.get("invalid", ""))
            result += f"## edge_id: {key} \n\n jump_condition: {jump_condition}\n\n from_node_index: {from_node_index}\n\n to_node_index:{to_node_index}\n\n invalid:{invalid}\n\n"
        return result

    @classmethod
    def generate_diff_text_by_content(cls, cur_content, diff_content):
        cur_text = cls.extract_text_from_content(cur_content)
        diff_text = cls.extract_text_from_content(diff_content)
        return cur_text, diff_text

    def generate_diff_htmls_by(self, diff_orchestrator, diff_commit_info):
        cur_content = self.to_dict()
        diff_content = diff_orchestrator.get_history_content_by_commit_info(
            diff_commit_info
        )
        cur_text, diff_text = self.generate_diff_text_by_content(
            cur_content, diff_content
        )
        orchestrator_diff_url, orchestrator_diff_text = generate_diff_html_by_text(
            diff_text, cur_text
        )
        cur_assistants: list[AssistantMeta, LLM] = self.extract_assistant_list()
        diff_assistants: list[AssistantMeta, LLM] = (
            diff_orchestrator.extract_assistant_list()
        )
        result = (
            [
                DiffResult.build_from_orchestrator(
                    self,
                    diff_orchestrator,
                    diff_commit_info,
                    orchestrator_diff_url,
                    orchestrator_diff_text,
                )
            ]
            if orchestrator_diff_url
            else []
        )
        for assistant, _ in cur_assistants:
            for diff_assistant, _ in diff_assistants:
                if assistant.get_id() == diff_assistant.get_id():
                    cur_commit_info = get_latest_commit_id(self.store_root())
                    cur_content = assistant.get_history_content_by_commit_info(
                        cur_commit_info
                    )
                    diff_content = diff_assistant.get_history_content_by_commit_info(
                        diff_commit_info
                    )
                    cur_text, diff_text = AssistantMeta.generate_diff_text_by_content(
                        cur_content, diff_content
                    )
                    assistant_diff_url, assistant_diff_text = (
                        generate_diff_html_by_text(diff_text, cur_text)
                    )

                    if assistant_diff_url:
                        result.append(
                            DiffResult.build_from_assistant(
                                assistant,
                                diff_assistant,
                                diff_commit_info,
                                assistant_diff_url,
                                assistant_diff_text,
                            )
                        )
        return result

    @classmethod
    def load_orchestrators_from(cls, orchest_type: str, branch: str):
        choices = []
        choices.append("")
        one_on_one_teacher_store_dir = cls.store_root()
        branch_dir_path = one_on_one_teacher_store_dir + orchest_type + "/" + branch
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
    def load_additional_args_list_from(cls, orchest_type: str, branch: str, name: str):
        one_on_one_teacher_store_dir = cls.store_root()
        orchestrator_file_path = (
            one_on_one_teacher_store_dir
            + orchest_type
            + os.sep
            + branch
            + os.sep
            + name
        )
        result = json.load(open(orchestrator_file_path, "r"))
        keys_list = result.get("additional_args_dict", {}).keys()
        return [""] + list(keys_list)

    @classmethod
    def build_from(cls, orchest_type: str, branch: str, orchestrator: str):
        orchest_file_path = (
            cls.store_root() + orchest_type + os.sep + branch + os.sep + orchestrator
        )

        with open(orchest_file_path, "r") as f:
            orchest_json = json.load(f)
            cur_orchestrator = cls.build_raw_orchestrator_from(
                orchest_type, branch, orchestrator, orchest_json
            )

        return cur_orchestrator

    @classmethod
    def build_raw_orchestrator_from(
        cls, orchest_type: str, branch: str, name: str, orchest_json: dict
    ):
        orchestrator = Orchestrator()
        orchestrator.raw_start_node_index = int(orchest_json["raw_start_node_index"])
        orchestrator.raw_node_count = int(orchest_json["raw_node_count"])
        orchestrator.raw_edge_count = int(orchest_json["raw_edge_count"])
        orchestrator.orchest_type = orchest_type
        orchestrator.branch = branch
        orchestrator.name = name
        previous_orchestrator_summary = orchest_json.get(
            "previous_orchestrator_summary", None
        )
        if previous_orchestrator_summary:
            orchestrator.previous_orchestrator_summary = OrchestratorAtCommit(
                Orchestrator.build_from(
                    previous_orchestrator_summary["orchest_type"],
                    previous_orchestrator_summary["branch"],
                    previous_orchestrator_summary["name"],
                ),
                previous_orchestrator_summary["commit_id"],
            )
        main_assistant_list = orchest_json.get("main_assistant_list", None)
        visible_assistants = orchest_json.get("visible_assistants", [])
        if main_assistant_list:
            orchestrator.main_assistant_list = main_assistant_list
        if visible_assistants:
            orchestrator.visible_assistants = visible_assistants
        orchestrator.additional_args = orchest_json.get("additional_args", "")
        orchestrator.additional_args_key = orchest_json.get("additional_args_key", "")
        orchestrator.additional_args_dict = orchest_json.get("additional_args_dict", {})
        if (
            orchestrator.additional_args_key
            and orchestrator.additional_args_key in orchestrator.additional_args_dict
        ):
            orchestrator.additional_args = orchestrator.additional_args_dict[
                orchestrator.additional_args_key
            ]

        for node_index, raw_node_dict in orchest_json["raw_node"].items():
            raw_node = RawNode()
            raw_node.from_dict(raw_node_dict)
            orchestrator.raw_node_dict[int(node_index)] = raw_node

        for edge_index, raw_edge_dict in orchest_json["raw_edge"].items():
            raw_edge = RawEdge()
            raw_edge.from_dict(raw_edge_dict)
            orchestrator.raw_edge_dict[int(edge_index)] = raw_edge
        return orchestrator

    def _init_all_nodes(self, trace_info: TraceInfo, llm: LLM):
        for node_index, raw_node in self.raw_node_dict.items():
            if raw_node.invalid:
                continue
            node = OrchestratorNode.build_from(
                node_index,
                raw_node,
                self.assistant_id_2_whole_context,
                self.additional_args,
                trace_info,
                llm,
            )
            self.id_2_node[node_index] = node

    def build_graph(self, trace_info: TraceInfo, llm: LLM):
        self._init_all_nodes(trace_info, llm)
        self.start_node = self.id_2_node[self.raw_start_node_index]

        for raw_edge in self.raw_edge_dict.values():
            if raw_edge.invalid:
                continue
            from_node = self.id_2_node[raw_edge.from_node_index]
            to_node = self.id_2_node[raw_edge.to_node_index]
            edge = OrchestratorEdge(
                from_node=from_node,
                to_node=to_node,
                jump_condition=raw_edge.jump_condition,
            )
            self.add_edge(edge)

    def add_edge(
        self,
        edge: OrchestratorEdge,
    ):
        if edge.from_node.id not in self.outgoing_edges:
            self.outgoing_edges[edge.from_node.id] = []
        self.outgoing_edges[edge.from_node.id].append(edge)

    def reset(self):
        self.start_node: OrchestratorNode = None
        self.id_2_node: dict[int, OrchestratorNode] = {}
        self.outgoing_edges: dict[int, list[OrchestratorEdge]] = {}

    async def travel_with_generator(
        self,
        cur_round_user_msg_info: dict,
        trace_info: TraceInfo,
        llm: LLM,
    ):
        self.reset()
        self.build_graph(trace_info, llm)
        cur_node = self.start_node
        this_round_new_msgs = []
        while cur_node:
            cur_node.do_preprocess(cur_round_user_msg_info)
            new_msgs = await cur_node.execute()
            this_round_new_msgs += new_msgs
            yield this_round_new_msgs
            cur_node.do_postprocess()
            cur_node = self._next_node_of(cur_node)

    async def travel_with_callback(
        self,
        cur_round_user_msg_info: dict,
        trace_info: TraceInfo,
        llm: LLM,
        on_new_delta,
    ):
        self.reset()
        self.build_graph(trace_info, llm)
        cur_node = self.start_node
        while cur_node:
            self.node_travel_history.append(cur_node.id)
            cur_node.do_preprocess(cur_round_user_msg_info)
            await cur_node.execute(
                on_new_delta=on_new_delta, visible_assistants=self.visible_assistants
            )
            cur_node.do_postprocess()
            cur_node = self._next_node_of(cur_node)

    def _next_node_of(self, cur_node: OrchestratorNode):
        cur_node_id = cur_node.id
        if cur_node_id not in self.outgoing_edges:
            return None
        possible_edge_list = self.outgoing_edges[cur_node_id]
        for edge in possible_edge_list:
            if edge.is_activated():
                return edge.to_node
        return None

    def get_original_messages(self):
        original_messages = []
        for node in self.id_2_node.values():
            for whole_context in node.whole_context_list:
                original_messages += whole_context.original_messages
        original_messages.sort(key=lambda x: x["timestamp"])
        return original_messages

    def get_additional_args_by_key(self):
        return self.additional_args_dict.get(
            self.additional_args_key, self.additional_args
        )

    def clear(self):
        for assistant_id, whole_context in self.assistant_id_2_whole_context.items():
            whole_context.clear()

    def raw_edge_info_of(self, edge_index: int, type: str):
        if (
            type == "jump_condition"
            and edge_index in self.raw_edge_dict
            and self.raw_edge_dict[edge_index].jump_condition
        ):
            return self.raw_edge_dict[edge_index].jump_condition
        elif type == "jump_condition":
            return RawEdge().jump_condition
        elif type == "invalid" and edge_index in self.raw_edge_dict:
            return self.raw_edge_dict[edge_index].invalid
        elif type == "invalid":
            return RawEdge().invalid
        elif (
            type == "to_node_index"
            and edge_index in self.raw_edge_dict
            and isinstance(self.raw_edge_dict[edge_index].to_node_index, int)
        ):
            return self.raw_edge_dict[edge_index].to_node_index
        elif type == "to_node_index":
            return RawEdge().to_node_index
        elif (
            type == "from_node_index"
            and edge_index in self.raw_edge_dict
            and isinstance(self.raw_edge_dict[edge_index].from_node_index, int)
        ):
            return self.raw_edge_dict[edge_index].from_node_index
        elif type == "from_node_index":
            return RawEdge().from_node_index

    def raw_node_info_of(self, node_index: int, type: str):
        if (
            type == "preprocess_func"
            and node_index in self.raw_node_dict
            and self.raw_node_dict[node_index].preprocess_func
        ):
            return self.raw_node_dict[node_index].preprocess_func
        elif type == "preprocess_func":
            return RawNode().preprocess_func
        elif (
            type == "postprocess_func"
            and node_index in self.raw_node_dict
            and self.raw_node_dict[node_index].postprocess_func
        ):
            return self.raw_node_dict[node_index].postprocess_func
        elif type == "postprocess_func":
            return RawNode().postprocess_func
        elif (
            type == "node_info"
            and node_index in self.raw_node_dict
            and self.raw_node_dict[node_index].node_info
        ):
            return self.raw_node_dict[node_index].node_info
        elif type == "node_info":
            return RawNode().node_info
        elif type == "invalid" and node_index in self.raw_node_dict:
            return self.raw_node_dict[node_index].invalid
        elif type == "invalid":
            return RawNode().invalid

    def gen_url(self):
        base_url = os.getenv("LAB_BOT_URL")
        parsed = urlparse(base_url)

        query_dict = {
            "_tab": "orchestrator",
            "orchest_type": self.orchest_type,
            "branch": self.branch,
            "name": self.name,
        }

        encoded_query = urlencode(query_dict)

        url = urlunparse(parsed._replace(query=encoded_query))
        return url

    def gen_href(self) -> str:
        return f"""<a href="{self.gen_url()}" target="_blank">打开assistant URL</a>"""

    def fork_to(self, forked_to_orchestrator_type, forked_to_branch_name: str):
        def update_forked_raw_node_info(raw_node_info: str, forked_to_branch_name):
            raw_node_info_dict: dict[str, list] = yaml.load(
                raw_node_info, Loader=yaml.FullLoader
            )
            for key, value in raw_node_info_dict.items():
                forked_from_branch = value[0]["branch"]
                cur_assistant_version = value[0]["assistant_version"]
                value[0][
                    "assistant_version"
                ] = f"fork-from-{forked_from_branch}-{cur_assistant_version}"
                value[0]["branch"] = forked_to_branch_name
            return yaml.dump(raw_node_info_dict)

        assistants_in_orchestration = self.extract_assistant_list()

        for node_index, raw_node in self.raw_node_dict.items():
            raw_node.id = node_index
            forked_raw_node_info = update_forked_raw_node_info(
                raw_node.node_info, forked_to_branch_name
            )
            raw_node.node_info = forked_raw_node_info

        for assistant, _ in assistants_in_orchestration:
            assistant.save_as(
                assistant.assistant_name,
                forked_to_branch_name,
                f"fork-from-{assistant.branch}-{assistant.assistant_version}",
            )

        self.save_as(
            orchest_type=forked_to_orchestrator_type,
            branch=forked_to_branch_name,
            new_file_name=f"{self.name}-fork-from-{self.branch}",
        )

    def recover_history_from(self, messages):
        self.clear()

        assistant_id_2_history = {}
        for msg in messages:
            assistant_id = msg["assistant_id"]
            if assistant_id not in assistant_id_2_history:
                assistant_id_2_history[assistant_id] = []
            assistant_id_2_history[assistant_id].append(msg)

        for assistant_id in assistant_id_2_history.keys():
            assistant_id_2_history[assistant_id] = sorted(
                assistant_id_2_history[assistant_id], key=lambda x: x["timestamp"]
            )

        for assistant_id, history in assistant_id_2_history.items():
            self.assistant_id_2_whole_context[assistant_id].recover_history_from(
                history
            )

    def deal_with_user_input(self, raw_user_input_dict: dict):
        raw_user_input_dict["content"] = raw_user_input_dict["raw_content"]
        return copy.deepcopy(raw_user_input_dict)

    def get_visible_msgs(self, new_msgs):
        return self.get_original_messages()
