import os
import sys
from typing import List

import requests

# 添加父目录到路径以导入 utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
  from utils import tavily_api_key
except ImportError:
  tavily_api_key = ""

# 优先使用 utils.py 配置，其次使用环境变量
TAVILY_API_KEY = tavily_api_key or os.getenv("TAVILY_API_KEY", "")
TAVILY_ENDPOINT = "https://api.tavily.com/search"


def tavily_search_snippets(query: str, max_results: int = 5) -> List[str]:
  """Call Tavily search API and return text snippets.

  This is a lightweight helper for the expert agent demo.
  If API key is missing or any error occurs, it returns an empty list
  instead of raising, so the caller can gracefully fall back.
  """
  query = (query or "").strip()
  if not query or not TAVILY_API_KEY:
    return []

  payload = {
    "api_key": TAVILY_API_KEY,
    "query": query,
    "search_depth": "basic",
    "max_results": max_results,
  }

  try:
    resp = requests.post(TAVILY_ENDPOINT, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
  except Exception:
    return []

  results = data.get("results", []) or []
  snippets: List[str] = []
  for item in results:
    title = item.get("title", "").strip()
    content = item.get("content", "").strip()
    if title or content:
      if title and content:
        snippets.append(f"{title}\n{content}")
      else:
        snippets.append(title or content)
  return snippets
