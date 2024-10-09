import base64
from datetime import datetime, timezone
import difflib
import os
import re
import subprocess
import uuid

import yaml

from .my_logger import LOGGER
from jinja2 import Environment

env = Environment()


STATE_PATTERN = r"<state>(.*?)<\/state>"


def extract_state_key_list_from_str(state_pattern: str, state_key_str: str) -> list:
    find_state = re.findall(state_pattern, state_key_str, re.DOTALL)
    state_keys = find_state[-1] if find_state else ""
    state_keys = state_keys.replace(" ", "").replace("\n", "")
    state_key_list = state_keys.split(",")
    state_key_list = [item for item in state_key_list if item]
    return state_key_list


def extract_state_dict_from_str(input: str) -> dict:
    import json

    state_dict = {}
    try:
        state_dict = json.loads(input)
    except Exception as e:
        LOGGER.exception("extract_state_dict_from_str error")
        LOGGER.exception(f"state_str: {input}")
    return state_dict


def choose_state_and_trans_to_str(state_dict: dict, chosen_state_key_list: list) -> str:
    chosen_state_str = ""
    for key, value in state_dict.items():
        if key in chosen_state_key_list:
            chosen_state_str += f"{key}: {value}\n"
    return chosen_state_str


def replace_state_pattern_str_by_state(
    state_pattern: str, state_str: str, state_pattern_str: str
) -> str:
    state_str = state_str.replace("\n", "")
    state_str = state_str.replace("\\", "")
    return re.sub(state_pattern, state_str, state_pattern_str)


def extract_addtional_args_from_str(additional_args: str) -> dict:
    if not additional_args:
        return {}
    try:
        return yaml.safe_load(additional_args)
    except yaml.YAMLError as exc:
        LOGGER.exception("extract_addtional_args_from_str error")
        return {}


def fill_str_with_additional_args_dict(
    additional_args_dict: dict, input_str: str
) -> str:
    if not additional_args_dict:
        return input_str
    try:
        for key, value in additional_args_dict.items():
            replace_key = "{" + key + "}"
            jinja_format_key = "{{" + key + "}}"
            if jinja_format_key not in input_str:
                # 兼容原有format逻辑, 需要之后数据清洗后下掉TODO:yuben
                input_str = input_str.replace(replace_key, jinja_format_key)
        input_str = env.from_string(input_str).render(additional_args_dict)
        return input_str
    except Exception as e:
        LOGGER.exception("fill_str_with_additional_args_dict error")
        return input_str


def parseNotionPageIdFromURL(notion_url: str):
    page_id = notion_url.split("/")[-1].split("?")[0].split("-")[-1]
    return page_id


def block_str_representer(dumper, data: str):
    # strip the new line in head and tail
    data = data.strip()
    if "\n" in data:
        # 对于包含换行的字符串，使用块格式
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    else:
        # 对于不包含换行的字符串，使用默认的处理方式
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def dump_as_yaml(data: dict | list | str) -> str:
    yaml.add_representer(str, block_str_representer)
    return yaml.dump(
        data, allow_unicode=True, default_flow_style=False, sort_keys=False
    )


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def encode_image_bytes(image_in_bytes: bytes):
    return base64.b64encode(image_in_bytes).decode("utf-8")


def extract_commit_id_and_datetime(string):
    import re

    pattern = (
        r"\b[A-Za-z]{3}\s[A-Za-z]{3}\s\d{1,2}\s\d{2}:\d{2}:\d{2}\s\d{4}\s[+-]\d{4}\b"
    )
    match = re.search(pattern, string)
    if match:
        commit_time = match.group(0)
        commit_id = string[:7]
        return commit_id + "-" + commit_time
    else:
        return None


def generate_commit_infos_from(file_path, cwd_path):
    result = subprocess.run(
        ["git", "log", "--pretty=format:%H %an %ad %s", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd_path,
    )
    commit_logs = result.stdout.strip().split("\n")
    commit_infos = [
        extract_commit_id_and_datetime(commit_log) for commit_log in commit_logs
    ]
    return commit_infos


def extract_datetime_from(commit_info):
    dt_string = commit_info.split("-")[1]
    dt_format = "%a %b %d %H:%M:%S %Y %z"
    parsed_time = datetime.strptime(dt_string, dt_format)
    return parsed_time


def filter_history_versions_before(commit_infos, last_commit_info):
    oldest_commit_time = extract_datetime_from(last_commit_info)
    commit_infos = [
        commit_info
        for commit_info in commit_infos
        if extract_datetime_from(commit_info) <= oldest_commit_time
    ]
    return sort_commit_infos(commit_infos)


def sort_commit_infos(commit_infos):
    now = datetime.now(timezone.utc)
    commit_infos = [commit_info for commit_info in commit_infos if commit_info]

    def sort_key(commit_info):
        parsed_time = extract_datetime_from(commit_info)
        return abs((parsed_time - now).total_seconds())

    commit_infos.sort(key=sort_key, reverse=False)
    return commit_infos


def filter_and_sort_commit_infos(commit_infos, oldest_commit_info):
    oldest_commit_time = extract_datetime_from(oldest_commit_info)
    commit_infos = [
        commit_info
        for commit_info in commit_infos
        if extract_datetime_from(commit_info) >= oldest_commit_time
    ]
    return sort_commit_infos(commit_infos)


def generate_diff_html_by_text(with_text, cur_text):
    diff_html = difflib.HtmlDiff().make_file(
        with_text.splitlines(),
        cur_text.splitlines(),
        context=True,
    )
    no_differences_count = diff_html.count("No Differences Found")
    # 代表diff 中没有add，也没有sub
    if no_differences_count == 2:
        return None, None

    diff = difflib.unified_diff(
        with_text.splitlines(), cur_text.splitlines(), lineterm=""
    )
    diff_text = "\n".join(diff)

    import re

    matche_css = re.findall(
        r'<table class="diff" id="difflib_chg_to\d+__top"', diff_html
    )
    style_css = (
        "<style>.diff td { white-space: pre-wrap; word-wrap: break-word; }</style>"
    )
    replace_str = style_css + matche_css[0]
    diff_html = diff_html.replace(matche_css[0], replace_str)

    diff_dir = os.getenv("ONE_ON_ONE_DIFF_DIR")

    diff_file_name = (
        f"""diff_{datetime.now().strftime("%Y-%m-%d")}_{uuid.uuid4()}.html"""
    )
    file_path = diff_dir + diff_file_name
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(diff_html)
    diff_url = f"""{os.getenv("ONE_ON_ONE_DIFF_URL_PREFIX")}{diff_file_name}"""
    return (
        diff_url,
        diff_text,
    )


def get_latest_commit_id(cwd_path, file_path=None):
    if not file_path:
        command = ["git", "log", "-1", "--pretty=format:%H %an %ad %s"]
    else:
        command = ["git", "log", "-1", "--pretty=format:%H %an %ad %s", file_path]
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd_path,
    )
    commit_log = result.stdout.strip()
    commit_info = extract_commit_id_and_datetime(commit_log)
    return commit_info


def push_new_commit_with(file_path, root_path):
    subprocess.run(["git", "add", file_path], cwd=root_path)
    subprocess.run(
        ["git", "commit", "-m", "--ADD: new assistant version"],
        cwd=root_path,
    )

    subprocess.run(
        ["git", "pull", "origin", "main", "--rebase"],
        cwd=root_path,
    )

    subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=root_path,
    )
