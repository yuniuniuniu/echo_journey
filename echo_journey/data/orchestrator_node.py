import asyncio
import copy

import yaml

from echo_journey.data.llms.llm import LLM
from echo_journey.data.llms.llm_utils import create_llm

from .assistant_meta import AssistantMeta
from .raw_node import RawNode
from .whole_context import WholeContext


class OrchestratorNode:
    def __init__(
        self,
        id,
        assistant_with_llm_list: list[tuple[AssistantMeta, LLM]],
        preprocess_func: str,
        postprocess_func: str,
        assistant_id_2_whole_context: dict[str, WholeContext],
        additional_args: str = "",
    ) -> None:
        self.id: int = id
        self.preprocess_func: str = preprocess_func
        self.postprocess_func: str = postprocess_func
        self.assistant_id_2_whole_context: dict[str, WholeContext] = (
            assistant_id_2_whole_context
        )
        self.whole_context_list: list[WholeContext] = []

        for assistant, llm in assistant_with_llm_list:
            assistant_id = assistant.get_id()
            if assistant_id in self.assistant_id_2_whole_context:
                chat_history = self.assistant_id_2_whole_context[
                    assistant_id
                ].cur_chat_history
            else:
                chat_history = []
            whole_context = WholeContext.rebuild_from(
                assistant_meta=assistant,
                chat_history=chat_history,
                llm=llm,
                additional_args=additional_args,
            )
            self.assistant_id_2_whole_context[assistant_id] = whole_context
            self.whole_context_list.append(whole_context)

    async def execute(
        self, on_new_delta=None, visible_assistants: list[AssistantMeta] = []
    ):
        async def _run_assistant(whole_context: WholeContext):
            last_bot_res_list = []
            assistant_id = whole_context.cur_visible_assistant.get_id()
            visible = any(
                assistant.get_id() == assistant_id for assistant in visible_assistants
            )

            bot_req = whole_context.cur_chat_history[-1]
            async for bot_res_list, delta in whole_context.submit():
                if on_new_delta and visible:
                    await on_new_delta(assistant_id, bot_req, bot_res_list, delta)
                last_bot_res_list = bot_res_list

            if on_new_delta:
                await on_new_delta(
                    assistant_id,
                    bot_req,
                    last_bot_res_list,
                    {"content": ""},
                    is_assistant_request_completed=True,
                )

            for bot_res in bot_res_list:
                whole_context.add_assistant_msg_to_cur(bot_res)
            return bot_res_list

        tasks = []
        for whole_context in self.whole_context_list:
            tasks.append(_run_assistant(whole_context))
        tasks_result = await asyncio.gather(*tasks)
        flat_tasks_result = []
        for task_result in tasks_result:
            flat_tasks_result += task_result
        return flat_tasks_result

    def do_preprocess(self, cur_round_user_msg_info):
        namespace = {
            "cur_round_user_msg_info": cur_round_user_msg_info,
            "assistant_id_2_whole_context": self.assistant_id_2_whole_context,
            "cur_node_id": str(self.id),
        }
        exec(self.preprocess_func, namespace)

    def do_postprocess(self):
        if self.postprocess_func:
            namespace = {
                "assistant_id_2_whole_context": self.assistant_id_2_whole_context
            }
            exec(self.postprocess_func, namespace)
        else:
            pass

    @classmethod
    def extract_assistant_list_from(cls, raw_node: RawNode, llm: LLM):
        raw_node_info_dict = {}
        try:
            raw_node_info_dict: dict[str, list] = yaml.load(
                raw_node.node_info, Loader=yaml.FullLoader
            )
        except yaml.YAMLError as e:
            raise Exception("invalid node info format")

        assistant_list = []
        for key, value in raw_node_info_dict.items():
            if not key.startswith("assistant"):
                raise Exception("invalid node name")
            id = value[0]["id"]
            assistant_id = f"{raw_node.id}_{id}"
            assert len(value) == 1, "invalid assistant format"
            cur_assistant = AssistantMeta(
                assistant_name=value[0]["assistant_name"],
                branch=value[0]["branch"],
                assistant_version=value[0]["assistant_version"],
                id=assistant_id,
            )
            if "llm_name" in value[0]:
                assistant_list.append((cur_assistant, create_llm(value[0]["llm_name"])))
            else:
                assistant_list.append((cur_assistant, llm))

        return assistant_list

    @classmethod
    def build_from(
        cls,
        id,
        raw_node: RawNode,
        assistant_id_2_whole_context: dict[str, WholeContext],
        additional_args: str,
        llm: LLM,
    ):
        assistant_with_llm_list = cls.extract_assistant_list_from(raw_node, llm)
        orchestrator_node = OrchestratorNode(
            id=id,
            assistant_with_llm_list=assistant_with_llm_list,
            preprocess_func=raw_node.preprocess_func,
            postprocess_func=raw_node.postprocess_func,
            assistant_id_2_whole_context=assistant_id_2_whole_context,
            additional_args=additional_args,
        )
        return orchestrator_node
