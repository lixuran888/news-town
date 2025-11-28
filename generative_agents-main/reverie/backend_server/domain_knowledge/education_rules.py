# -*- coding: utf-8 -*-
"""教育局代表专用规则库。

每条规则包含：
- id: 规则编号，例如 "ED001"（Education）
- category: 类型
- text: 规则的自然语言表述
- guidance: 面向教育局代表的操作建议
"""
from typing import List, Dict


# 教育局代表规则库 - 待用户填充
# 规则编号前缀: ED (Education)
EDUCATION_RULES: List[Dict[str, str]] = [
  # ========== 示例规则（等待用户提供完整规则） ==========
  {"id": "ED001", "category": "示例", "text": "这是教育规则的示例占位符。", "guidance": "等待用户提供具体规则。"},
]


def retrieve_education_rules(query: str, top_k: int = 3) -> List[Dict[str, str]]:
  """按关键词匹配返回最多 top_k 条教育规则。

  匹配逻辑：
  - query 与规则文本/建议都转为小写
  - 用子串匹配统计命中 token 数
  - 得分为 0 的规则会被忽略；若全部为 0，则按原顺序取前 top_k 条
  """
  query = (query or "").strip()
  if not query:
    return EDUCATION_RULES[:top_k]

  q_tokens = [t for t in query.lower().replace("\n", " ").split(" ") if t]
  if not q_tokens:
    return EDUCATION_RULES[:top_k]

  scored = []
  for rule in EDUCATION_RULES:
    blob = f"{rule['text']} {rule['guidance']} {rule['category']}".lower()
    score = sum(1 for t in q_tokens if t in blob)
    if score > 0:
      scored.append((score, rule))

  if not scored:
    return EDUCATION_RULES[:top_k]

  scored.sort(key=lambda x: x[0], reverse=True)
  return [r for _, r in scored[:top_k]]


def format_education_rules_for_prompt(rules: List[Dict[str, str]]) -> str:
  """将若干条教育规则格式化为多行文本，便于塞进 LLM prompt。"""
  lines: List[str] = []
  for r in rules:
    line = f"[{r['id']}]({r['category']}): {r['text']} 建议：{r['guidance']}"
    lines.append(line)
  return "\n".join(lines) if lines else "(当前教育规则库未返回匹配项)"
