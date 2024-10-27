import sys
from pypinyin import Style

sys.path.append("/root/echo_journey")
from echo_journey.common.utils import parse_pinyin


data = parse_pinyin("睡觉")
print(data)