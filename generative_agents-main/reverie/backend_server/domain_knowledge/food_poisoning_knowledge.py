import os
from typing import List


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_FILE = os.path.join(BASE_DIR, "food_poisoning_case_1.txt")


def _load_corpus() -> str:
  """Load the raw corpus text for food poisoning domain.

  For now we only have a single case file, but this can be extended to
  multiple files later.
  """
  with open(CASE_FILE, "r", encoding="utf-8") as f:
    return f.read()


def _split_paragraphs(text: str) -> List[str]:
  """Split corpus into non-empty paragraphs."""
  parts = [p.strip() for p in text.split("\n\n")]
  return [p for p in parts if p]


def retrieve_food_poisoning_knowledge(query: str, top_k: int = 3) -> List[str]:
  """Return up to top_k relevant paragraphs for the given query.

  Simple keyword-based retrieval:
  - lowercases both query and paragraphs
  - scores each paragraph by how many query tokens it contains
  - returns the best-scoring paragraphs in original text form
  """
  query = (query or "").strip()
  if not query:
    return []

  text = _load_corpus()
  paragraphs = _split_paragraphs(text)
  if not paragraphs:
    return []

  q_tokens = [t for t in query.lower().replace("\n", " ").split(" ") if t]
  if not q_tokens:
    return []

  scored = []
  for p in paragraphs:
    lp = p.lower()
    score = sum(1 for t in q_tokens if t in lp)
    if score > 0:
      scored.append((score, p))

  if not scored:
    # 没有命中关键字时，就按原顺序返回前 top_k 段
    return paragraphs[:top_k]

  scored.sort(key=lambda x: x[0], reverse=True)
  return [p for _, p in scored[:top_k]]
