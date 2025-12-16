import datetime
import random
import subprocess
import hashlib


def get_timestamp_and_hash():
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")

    random_int = random.getrandbits(128)
    random_hash = hashlib.sha256(str(random_int).encode()).hexdigest()[:8]  # Shorten to 8 chars

    return f"{timestamp}-{random_hash}"


def count_lines(file_path):
    result = subprocess.run(['wc', '-l', file_path], capture_output=True, text=True)
    return int(result.stdout.split()[0])

# Costs in USD per 1M tokens, [input, output]
# See https://platform.openai.com/docs/pricing
LLM_COST_MAPPING = {
    "nf-gpt-4o-mini": [0.4, 1.6],
    "gpt-5.1": [1.25, 10]
}
