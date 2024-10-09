import asyncio
import copy
import time

import openai

from ..llm import LLM
from ..my_logger import LOGGER


class OpenaiLLM(LLM):
    def __init__(self, config_name="OpenaiLLM", **kwargs):
        self.api_key = kwargs.get("api_key", None)
        self.api_type = kwargs.get("api_type", None)
        self.api_base = kwargs.get("api_base", None)
        self.api_version = kwargs.get("api_version", None)
        self.deployment_id = kwargs.get("deployment_id", None)
        self.engine = kwargs.get("engine", None)
        self.model = kwargs.get("model", None)
        self.max_tokens = kwargs.get("max_tokens", None)
        self.config_name = config_name

    def _to_config_dict(self):
        config_dict = copy.deepcopy(vars(self))
        for key in list(config_dict.keys()):
            if key == "config_name" or config_dict[key] is None:
                del config_dict[key]
        return config_dict

    def get_config_name(self):
        return self.config_name

    def commit(
        self,
        messages: list[dict],
        functions: list[dict] = None,
        temperature=0,
        json_mode=False,
        **kwargs,
    ):
        retry_count = 0
        while True:
            try:
                config_dict = self._to_config_dict()
                if functions:
                    config_dict["functions"] = functions
                if temperature:
                    config_dict["temperature"] = temperature
                if messages:
                    config_dict["messages"] = messages

                extra_control_params = dict()
                if json_mode:
                    extra_control_params["response_format"] = {"type": "json_object"}

                response = openai.ChatCompletion.create(
                    **config_dict, **extra_control_params
                )

                return response.choices[0]["message"]["content"]
            except Exception as e:
                retry_count += 1
                LOGGER.exception(
                    "commit_to_llm failed, retry count: {}, messages: {}",
                    retry_count,
                    messages,
                )
                if retry_count > 3:
                    raise e
                else:
                    sleep_list = [0, 60, 120, 180]
                    time.sleep(sleep_list[retry_count])

    async def acommit(
        self,
        messages: list[dict],
        functions: list[dict] = None,
        temperature=0,
        json_mode=False,
        **kwargs,
    ):

        # assert message["content"]的总长度小于100K
        assert sum([len(message["content"]) for message in messages]) < 100 * 1000

        while True:
            try:
                config_dict = self._to_config_dict()
                if functions:
                    config_dict["functions"] = functions

                extra_control_params = dict()
                if json_mode:
                    extra_control_params["response_format"] = {"type": "json_object"}

                response = await openai.ChatCompletion.acreate(
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                    **extra_control_params,
                    **config_dict,
                )

                async for chunk in response:
                    if (
                        chunk
                        and len(chunk["choices"]) > 0
                        and "delta" in chunk["choices"][0]
                    ):
                        await asyncio.sleep(0)
                        yield chunk["choices"][0]["delta"], None
                        await asyncio.sleep(0)
                break
            except Exception as e:
                LOGGER.exception(
                    "commit_to_llm_async failed, retry messages: {}",
                    messages,
                )
                raise e
