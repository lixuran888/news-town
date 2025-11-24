from typing import List

from persona.prompt_template.gpt_structure import ChatGPT_single_request
from domain_knowledge.food_poisoning_knowledge import retrieve_food_poisoning_knowledge
from domain_knowledge.food_safety_rules import (
  retrieve_food_safety_rules,
  format_rules_for_prompt,
)
from web_search.tavily_client import tavily_search_snippets


def expert_answer(question: str) -> str:
  """Food-poisoning expert demo.

  - Uses keyword retrieval over local domain knowledge.
  - Optionally calls Tavily web search to fetch recent policies/news.
  - Feeds local snippets + Tavily snippets + question into the LLM.
  - Returns the expert-style analysis / policy suggestion.

  This is a standalone demo and does not yet integrate with persona
  memories or the simulation loop.
  """
  if not question or not question.strip():
    return "(empty question)"

  # 本地知识库检索：案例叙事
  snippets: List[str] = retrieve_food_poisoning_knowledge(question, top_k=3)
  local_block = "\n\n".join(snippets) if snippets else "(本地知识库暂无匹配片段，按常识回答)"

  # 本地知识库检索：结构化规则（FS 编号）
  rules = retrieve_food_safety_rules(question, top_k=3)
  rules_block = format_rules_for_prompt(rules)

  # Tavily 联网检索：聚焦中国校园食物中毒、食品安全政策与舆论
  tavily_query = "中国 校园 食物中毒 食品安全 政策 舆论 " + question.strip()
  tavily_results: List[str] = tavily_search_snippets(tavily_query, max_results=5)
  if tavily_results:
    tavily_block = "\n\n".join(tavily_results)
  else:
    tavily_block = "(暂未成功检索到近期公开报道或 Tavily API 未配置)"

  prompt = (
    "你是一名公共卫生与食品安全领域的资深专家，长期参与校园和集体供餐场景的风险评估与事故处置。\n"
    "下面会给你：\n"
    "1）与当前事件可能相关的本地案例知识片段；\n"
    "2）结构化的食品安全规则条文（带编号，可在回答中引用）；\n"
    "3）近期公开报道和政策舆论摘要；\n"
    "4）当前世界线中已经发生的事件与舆论（如果有，将在未来版本中提供）；\n"
    "5）具体提问。\n"
    "你的任务是综合这些信息，给出专业、审慎的分析和建议。\n\n"
    "【本地案例知识片段】:\n" + local_block + "\n\n"
    "【食品安全规则库条文】(可在回答中引用编号):\n" + rules_block + "\n\n"
    "【近期公开报道与政策舆论】(来自 Tavily 搜索):\n" + tavily_block + "\n\n"
    "【提问】:\n" + question.strip() + "\n\n"
    "请用简洁的中文回答，结构上尽量包含：\n"
    "1. 可能原因分析（不局限于食物中毒，需根据问题内容自行判断事件类型）；\n"
    "2. 风险评估（包括对健康、学校运行和社会舆论的影响）；\n"
    "3. 建议采取的具体措施（学校/管理部门/家长或其他相关方各自应该做什么），并在合适处提及相关政策依据。\n"
  )

  return ChatGPT_single_request(prompt)


if __name__ == "__main__":
  q = "这起校园食物中毒事件最可能的原因是什么？学校应该采取哪些措施？"
  print(expert_answer(q))
