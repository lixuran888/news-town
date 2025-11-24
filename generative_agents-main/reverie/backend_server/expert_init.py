import datetime
from typing import Dict, Iterable, List, Set

from persona.prompt_template.gpt_structure import ChatGPT_single_request, get_embedding
from persona.prompt_template.run_gpt_prompt import run_gpt_prompt_public_opinion
from persona.cognitive_modules.retrieve import new_retrieve
from domain_knowledge.food_poisoning_knowledge import retrieve_food_poisoning_knowledge
from domain_knowledge.food_safety_rules import (
  retrieve_food_safety_rules,
  format_rules_for_prompt,
)


FOOD_POISONING_EVENT_TEXT = (
  "[事件基本信息]\n"
  "2025年3月10日，x市Y中学发生校园食物中毒事件，多名学生在午餐后出现恶心、呕吐、腹泻等症状。\n\n"
  "[事件经过]\n"
  "当天中午学校食堂提供的午餐包括：红烧鸡块、土豆炖牛肉、清炒西兰花和米饭。\n"
  "据学生描述，部分菜品存在异味或颜色异常，但仍有相当一部分学生食用。\n"
  "首批学生在用餐后1小时左右开始出现呕吐和腹痛症状，随后陆续有学生被送往医院。\n\n"
  "[初步调查结果]\n"
  "卫生部门初步调查显示，疑似问题菜品为红烧鸡块和土豆牛肉。\n"
  "食堂留样食品中检出致病菌数量超出国家卫生标准。\n"
  "部分冷链储藏和再加热过程不符合食品安全操作规范。\n\n"
  "[后续处置]\n"
  "学校临时停用食堂并启动应急预案，对所有就餐学生进行排查和随访。\n"
  "教育局和市场监管部门介入调查，对涉事食堂进行整改和责任追究。\n"
  "官方发布通报，澄清网络谣言并公布最新调查进展。"
)

FOOD_POISONING_EVENT_KEYWORDS: Set[str] = {
  "食物中毒", "学校", "食堂", "学生", "午餐", "恶心", "呕吐", "腹泻", "冷链", "再加热"
}


# 供舆论收集使用的关键词集合（可以根据需要继续扩展）
PUBLIC_OPINION_KEYWORDS: Set[str] = {
  "食物中毒", "学校", "食堂", "学生", "午餐", "中毒", "食品安全", "舆论", "家长", "校园"
}


def inject_food_poisoning_event(persona, created_time: datetime.datetime) -> None:
  """Inject a shared campus food poisoning event into a persona's memory.

  This is called once at simulation initialization so that all agents
  (including future expert agents) share a common long-term memory of the
  incident.
  """
  try:
    created = created_time
    expiration = None
    s = persona.name  # 以“自己经历/感知到”的方式记录
    p = "经历"
    o = "校园食物中毒事件"

    description = FOOD_POISONING_EVENT_TEXT
    keywords = FOOD_POISONING_EVENT_KEYWORDS
    poignancy = 0.9
    embedding_key = "campus_food_poisoning_event"
    embedding_vec = get_embedding(description)
    embedding_pair = (embedding_key, embedding_vec)
    filling = []

    # 写入到长期记忆事件流
    persona.a_mem.add_event(
      created=created,
      expiration=expiration,
      s=s,
      p=p,
      o=o,
      description=description,
      keywords=keywords,
      poignancy=poignancy,
      embedding_pair=embedding_pair,
      filling=filling,
    )
  except Exception:
    # 初始化阶段尽量不要让整个模拟崩掉，失败就静默跳过
    return


def _is_expert_persona(persona) -> bool:
  """粗略判断一个 persona 是否是"专家"角色。

  目前先按名字包含 "Expert" 识别，后续如果有更多专家角色，
  可以改成读取 scratch / 配置里的显式 role 标签。
  """
  try:
    return "expert" in persona.name.lower()
  except Exception:
    return False


def collect_public_opinion_chats(personas: Dict[str, "Persona"],
                                 max_per_person: int = 20,
                                 max_total: int = 80,
                                 keywords: Iterable[str] = None) -> List[str]:
  """从多名平民 / 家长 persona 的聊天记忆中收集与校园食物中毒相关的言论。

  返回若干条格式化好的聊天片段文本，用于后续交给 GPT 汇总成民众舆论。
  """

  if keywords is None:
    keywords = PUBLIC_OPINION_KEYWORDS
  kw_lower = {k.lower() for k in keywords}

  snippets: List[str] = []

  for name, persona in personas.items():
    # 专家本身的发言先不算在“民众舆论”里
    if _is_expert_persona(persona):
      continue

    try:
      seq_chat = getattr(persona.a_mem, "seq_chat", [])
    except Exception:
      continue

    count_for_person = 0
    for chat_node in seq_chat:
      if count_for_person >= max_per_person or len(snippets) >= max_total:
        break

      # chat_node.keywords 是一个 set，里边是字符串关键词
      chat_kws = {str(k).lower() for k in getattr(chat_node, "keywords", set())}
      if not kw_lower.intersection(chat_kws):
        continue

      # description: 当前对话主题，filling: 实际轮次内容
      created = getattr(chat_node, "created", None)
      created_str = ""
      if isinstance(created, datetime.datetime):
        created_str = created.strftime("%Y-%m-%d %H:%M")

      # filling 是 [[speaker, utterance], ...]
      lines: List[str] = []
      for row in getattr(chat_node, "filling", []):
        if len(row) >= 2:
          lines.append(f"{row[0]}: {row[1]}")

      if not lines:
        continue

      snippet = f"[{created_str}] {name} 的一次对话:\n" + "\n".join(lines)
      snippets.append(snippet)
      count_for_person += 1

  return snippets


def generate_and_broadcast_public_opinion(personas: Dict[str, "Persona"],
                                          created_time: datetime.datetime) -> None:
  """生成民众舆论摘要，并写入所有专家 persona 的长期记忆。

  - 先从平民 / 家长的 seq_chat 中抓取与校园食物中毒相关的对话；
  - 使用 run_gpt_prompt_public_opinion 汇总成一段舆论摘要；
  - 以事件形式注入所有专家的 associative memory。
  """

  try:
    snippets = collect_public_opinion_chats(personas)
    if not snippets:
      return

    # 将多条聊天合并成一个长文本，交给 GPT 总结
    raw_text = "\n\n".join(snippets)
    opinion_summary = run_gpt_prompt_public_opinion(raw_text)[0]
    if not opinion_summary:
      return

    for persona in personas.values():
      if not _is_expert_persona(persona):
        continue

      try:
        created = created_time
        expiration = None
        s = "校园公众舆论"
        p = "围绕"
        o = "食物中毒事件的讨论"

        description = opinion_summary
        keywords = PUBLIC_OPINION_KEYWORDS
        poignancy = 0.7
        embedding_key = "campus_public_opinion_food_poisoning"
        embedding_vec = get_embedding(description)
        embedding_pair = (embedding_key, embedding_vec)
        filling: List = []

        persona.a_mem.add_event(
          created=created,
          expiration=expiration,
          s=s,
          p=p,
          o=o,
          description=description,
          keywords=keywords,
          poignancy=poignancy,
          embedding_pair=embedding_pair,
          filling=filling,
        )
      except Exception:
        # 不让单个专家注入失败影响整个循环
        continue
  except Exception:
    # 舆论生成失败时静默跳过，避免打断主循环
    return


def _select_relevant_memory_nodes(persona,
                                  question: str,
                                  max_memories: int) -> List["ConceptNode"]:
  focal_points = [
    "当前校园食物中毒事件",
    "公众舆论",
    "食品安全监管",
    question or "",
  ]
  retrieved = new_retrieve(persona, focal_points, n_count=max_memories)
  nodes: List["ConceptNode"] = []
  for lst in retrieved.values():
    for n in lst:
      if n not in nodes:
        nodes.append(n)
  return nodes[:max_memories]


def _format_memory_nodes_for_prompt(nodes: List["ConceptNode"]) -> str:
  if not nodes:
    return "(当前长期记忆中暂无与本议题高度相关的片段)"

  lines: List[str] = []
  for n in nodes:
    try:
      created_str = n.created.strftime("%Y-%m-%d %H:%M")
    except Exception:
      created_str = ""
    spo = " - ".join([str(n.subject), str(n.predicate), str(n.object)])
    line = f"[{created_str}] {spo}: {n.description}"
    lines.append(line)
  return "\n".join(lines)


def _format_public_opinion_from_nodes(nodes: List["ConceptNode"],
                                      max_public_opinion: int) -> str:
  if not nodes:
    return "(当前尚未形成明确的公众舆论摘要，或尚未写入专家记忆)"

  filtered: List["ConceptNode"] = []
  for n in nodes:
    kws = {str(k).lower() for k in getattr(n, "keywords", set())}
    if kws.intersection({k.lower() for k in PUBLIC_OPINION_KEYWORDS}):
      filtered.append(n)
  if not filtered:
    return "(当前尚未形成明确的公众舆论摘要，或尚未写入专家记忆)"

  filtered = filtered[:max_public_opinion]
  parts: List[str] = []
  for n in filtered:
    parts.append(str(n.description))
  return "\n".join(parts)


def expert_meeting_speech(persona,
                          question: str,
                          max_memories: int = 6,
                          max_rules: int = 3,
                          max_case_snippets: int = 3,
                          max_public_opinion: int = 1) -> str:
  """Generate an in-simulation expert speech for a meeting.

  The speech is grounded in:
  - retrieved long-term memories (including seeded cases and public opinion),
  - local food poisoning case knowledge paragraphs,
  - structured food safety rules (FS001–FS120).
  """

  if not question or not question.strip():
    return "(empty question)"

  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Expert")

  memory_nodes = _select_relevant_memory_nodes(persona, question, max_memories)
  memory_block = _format_memory_nodes_for_prompt(memory_nodes)

  case_snippets: List[str] = retrieve_food_poisoning_knowledge(
    question, top_k=max_case_snippets
  )
  if case_snippets:
    case_block = "\n\n".join(case_snippets)
  else:
    case_block = "(本地案例知识库暂无特别相关的历史案例片段)"

  rules = retrieve_food_safety_rules(question, top_k=max_rules)
  rules_block = format_rules_for_prompt(rules)

  opinion_block = _format_public_opinion_from_nodes(
    memory_nodes,
    max_public_opinion=max_public_opinion,
  )

  prompt = (
    f"你是一名公共卫生与食品安全领域的资深专家，目前正在参加一次围绕“校园食物中毒/食品安全”的专家咨询会议。"\
    f"请基于下列信息进行分析和发言：\n\n"
    f"【一、你在当前世界线中的长期记忆片段】（只列出若干最相关的）\n"\
    f"{memory_block}\n\n"
    f"【二、以往校园食物中毒案例的本地知识片段】\n"\
    f"{case_block}\n\n"
    f"【三、结构化食品安全规则库条文】（带编号，可在回答中引用）\n"\
    f"{rules_block}\n\n"
    f"【四、社会公众舆论与家长关切摘要】\n"\
    f"{opinion_block}\n\n"
    f"【五、本轮会议主持人交给你的具体问题】\n"\
    f"{question.strip()}\n\n"
    f"请你以“{name}”的身份，用简洁的中文，给出一段面向“主持人和其他与会者”的发言，要求：\n"
    f"1. 先简要指出你从长期记忆和以往案例中联想到的关键点（如制度缺陷、监管薄弱环节、信息透明度等），必要时可以引用 FS 规则编号（例如“根据 FS012...”）。\n"
    f"2. 分析当前事件在健康风险、学校运行和社会舆论方面的主要风险点。\n"
    f"3. 给出对学校、监管部门和家长分别的操作性建议，明确哪些是“立刻要做的”、哪些是“中长期需要改进的制度”。\n"
    f"4. 全程保持专业、克制，但对受害学生和家长表达同理心，避免过度技术化或冷漠表述。\n"
  )

  return ChatGPT_single_request(prompt)
