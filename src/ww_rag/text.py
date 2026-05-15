from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if re.search(r"[\u4e00-\u9fff]", token) and len(token) > 2:
            expanded.extend(token[i : i + 2] for i in range(len(token) - 1))
            expanded.extend(token[i : i + 3] for i in range(len(token) - 2))
    return expanded


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha256(path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def text_vector(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    counts = Counter(tokenize(text))
    for token, count in counts.items():
        bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dimensions
        vector[bucket] += 1.0 + math.log(count)
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))

