from .llm import LLM
from .llms.openai import OpenaiLLM
import yaml
import os


def _get_config_path() -> str:
    # 当前脚本的绝对路径
    current_script_path = os.path.abspath(__file__)

    # 当前脚本所在目录
    current_dir = os.path.dirname(current_script_path)

    # 基于当前脚本所在目录的相对路径
    return os.path.join(current_dir, "llm_configs.yaml")


def create_llm(config_name: str) -> LLM:
    llm_config = get_llm_config(config_name)

    if llm_config["api_type"] in ["azure", "openai"]:
        return OpenaiLLM(config_name, **llm_config)
    else:
        raise ValueError(f"Unknown api_type: {llm_config['api_type']}")


def get_llm_config(config_name):
    with open(_get_config_path(), "r") as yaml_file:
        yaml_data: dict = yaml.safe_load(yaml_file)
    llm_config = yaml_data[config_name]
    return llm_config


def get_llm_names() -> list[str]:
    with open(_get_config_path(), "r") as yaml_file:
        yaml_data: dict = yaml.safe_load(yaml_file)
    return list(yaml_data.keys())


def create_default_llm() -> LLM:
    # This is set to `azure`
    api_type = "azure"
    api_key = os.getenv("CUSTOM_OPENAI_KEY")
    # The base URL for your Azure OpenAI resource. e.g. "https://<your resource name>.openai.azure.com"
    api_base = os.getenv("CUSTOM_OPENAI_API_BASE")
    # Currently Chat Completions API have the following versions available: 2023-03-15-preview
    api_version = os.getenv("CUSTOM_OPENAI_API_VERSION")
    llm = OpenaiLLM(
        api_type=api_type,
        api_key=api_key,
        api_base=api_base,
        api_version=api_version,
    )
    return llm
