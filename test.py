from pypinyin import pinyin, Style

text = "啊微"

# 获取带调号的拼音
pinyin_with_tone = pinyin(text, style=Style.TONE3)

# 获取声母
initials = pinyin(text, style=Style.INITIALS)

# 获取带调号的韵母
finals_with_tone = pinyin(text, style=Style.FINALS_TONE3)

print(pinyin_with_tone)
print(initials)
print(finals_with_tone)