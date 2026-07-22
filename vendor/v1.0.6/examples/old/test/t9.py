import os,re

text = """hello, world
abcdef
<speak>This should be
lets add new line...
spoken</speak>
more text...
"""
text = 'hello, world\n\
abcdef\n\
<speak>This should be spoken</speak>\n\
more text...\n'
# 1. Enable DOTALL so `.` matches newlines
pattern = re.compile(r'<speak>(.*?)</speak>', re.DOTALL | re.IGNORECASE)

# 2. Find all <speak>…</speak> blocks
blocks = pattern.findall(text)

for i, block in enumerate(blocks, 1):
    print(f"Block {i}:\n{block}\n")
