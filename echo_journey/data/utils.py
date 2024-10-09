import base64
import yaml

from jinja2 import Environment

env = Environment()


def extract_state_dict_from_str(input: str) -> dict:
    import json

    state_dict = {}
    try:
        state_dict = json.loads(input)
    except Exception as e:
        pass
    return state_dict

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def encode_image_bytes(image_in_bytes: bytes):
    return base64.b64encode(image_in_bytes).decode("utf-8")