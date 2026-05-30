### Streaming `<speak>` extraction + `spd‑say`
#python
import re
import subprocess

# ------------------------------------------------------------
# 1.  State that keeps the part of a <speak> block that is still
#     incomplete (because the closing tag hasn't arrived yet).
# ------------------------------------------------------------
incomplete = ""

# ------------------------------------------------------------
# 2.  Regex that matches a *complete* <speak>…</speak> block.
#     re.DOTALL lets `.` match newlines so the block can span
#     many chunks.
# ------------------------------------------------------------
block_pat = re.compile(r'<speak>(.*?)</speak>', re.IGNORECASE | re.DOTALL)

def speak(text: str):
    """Send a string to the system TTS."""
    print("speak(): {}".format(text))
    subprocess.run(['spd-say', text])

def process_chunk(chunk: str):
    """Call this every time a new chunk arrives."""
    global incomplete

    # Prepend any leftover text from the previous chunk
    data = incomplete + chunk

    # Find all complete blocks in the current data
    for match in block_pat.finditer(data):
        speak(match.group(1))

    # Anything after the last </speak> is the start of a new block
    last_end = 0
    for match in block_pat.finditer(data):
        last_end = match.end()
    incomplete = data[last_end:]   # keep the unfinished part

# ------------------------------------------------------------
# 3.  Example – simulate a stream
# ------------------------------------------------------------
if __name__ == "__main__":
    stream = [
        "hello, world\n",
        "<speak>This should be\n",
        "lets add new line...\n",
        "spoken</speak>\n",
        "more text...\n",
        "<speak>Second block\n",
        "still going...\n",
    ]

    for chunk in stream:
        process_chunk(chunk)

    # End of stream – flush any remaining partial block
    if incomplete.strip():
        # If we hit the end of the stream and still have an opening tag
        # without a closing tag, you can decide what to do.
        # Here we just speak whatever we have.
        speak(incomplete)
