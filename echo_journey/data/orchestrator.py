import json
import os

from echo_journey.data.llms.llm import LLM
from .assistant_meta import AssistantMeta
from .orchestrator_edge import OrchestratorEdge
from .orchestrator_node import OrchestratorNode
from .whole_context import WholeContext
from .raw_edge import RawEdge
from .raw_node import RawNode

class Orchestrator():
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

    def get_id(self):
        return f"{self.orchest_type}-{self.branch}-{self.name}"

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

    def _init_all_nodes(self, llm: LLM):
        for node_index, raw_node in self.raw_node_dict.items():
            if raw_node.invalid:
                continue
            node = OrchestratorNode.build_from(
                node_index,
                raw_node,
                self.assistant_id_2_whole_context,
                self.additional_args,
                llm,
            )
            self.id_2_node[node_index] = node

    def build_graph(self, llm: LLM):
        self._init_all_nodes(llm)
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
        llm: LLM,
    ):
        self.reset()
        self.build_graph(llm)
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
        llm: LLM,
        on_new_delta,
    ):
        self.reset()
        self.build_graph(llm)
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

    def clear(self):
        for assistant_id, whole_context in self.assistant_id_2_whole_context.items():
            whole_context.clear()