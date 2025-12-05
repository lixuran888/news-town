import datetime
from typing import Dict, Iterable, List, Set

from persona.prompt_template.gpt_structure import ChatGPT_single_request, get_embedding
from persona.prompt_template.run_gpt_prompt import run_gpt_prompt_public_opinion
from persona.cognitive_modules.retrieve import new_retrieve
from persona.cognitive_modules.phone_browsing import get_online_opinions_for_experts
from domain_knowledge.food_poisoning_knowledge import retrieve_food_poisoning_knowledge
from domain_knowledge.food_safety_rules import (
  retrieve_food_safety_rules,
  format_rules_for_prompt,
)
from domain_knowledge.market_supervision_rules import (
  retrieve_market_supervision_rules,
  format_market_supervision_rules_for_prompt,
)
from domain_knowledge.education_rules import (
  retrieve_education_rules,
  format_education_rules_for_prompt,
)
from domain_knowledge.moderator_rules import (
  retrieve_moderator_rules,
  format_moderator_rules_for_prompt,
)
from web_search.tavily_client import tavily_search_snippets


# 全局变量：存储最后一次专家发言的思考过程
_last_expert_reasoning = {}


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

  通过精确匹配专家角色名称。
  """
  try:
    name_lower = persona.name.lower()
    # 排除主持人
    if "moderator" in name_lower or "主持" in name_lower:
      return False
    
    # 精确匹配已知的专家角色名称
    known_expert_names = [
      "public health expert",
      "market supervision expert", 
      "education expert",
      "education representative",
      "education bureau representative",  # 实际使用的名称
      "公共卫生专家",
      "市场监管专家",
      "教育局代表",
    ]
    for expert_name in known_expert_names:
      if expert_name in name_lower:
        return True
    
    # 宽松匹配：名字包含 "expert" 或 "代表" 或 "专家"
    if "expert" in name_lower or "代表" in name_lower or "专家" in name_lower:
      return True
      
    return False
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
                                  max_memories: int,
                                  meeting_time: datetime.datetime = None) -> List["ConceptNode"]:
  """检索与议题相关的记忆节点。
  
  Args:
    persona: 角色对象
    question: 议题/问题
    max_memories: 最大返回数量
    meeting_time: 会议时间，用于计算24小时时间窗口（前一天23:00到今天23:00）
  """
  focal_points = [
    "当前校园食物中毒事件",
    "公众舆论",
    "食品安全监管",
    question or "",
  ]
  retrieved = new_retrieve(persona, focal_points, n_count=max_memories * 3)  # 多检索一些，因为要过滤
  
  # 计算24小时时间窗口：前一天23:00 到 今天23:00
  if meeting_time:
    # 会议时间是今天23:00，往前推24小时就是昨天23:00
    time_window_start = meeting_time - datetime.timedelta(hours=24)
    time_window_end = meeting_time
  else:
    time_window_start = None
    time_window_end = None
  
  nodes: List["ConceptNode"] = []
  for lst in retrieved.values():
    for n in lst:
      if n not in nodes:
        # 如果指定了时间窗口，过滤掉窗口外的记忆
        if time_window_start and time_window_end:
          try:
            node_time = n.created
            if node_time < time_window_start or node_time > time_window_end:
              continue  # 跳过不在时间窗口内的记忆
          except Exception:
            pass  # 如果无法获取时间，保留该记忆
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
                                      max_public_opinion: int,
                                      sim_folder: str = None,
                                      curr_time: datetime.datetime = None) -> str:
  """格式化公众舆论，包括线下对话和线上发言"""
  parts: List[str] = []
  
  # 1. 线下舆论（从记忆节点中提取）
  if nodes:
    filtered: List["ConceptNode"] = []
    for n in nodes:
      kws = {str(k).lower() for k in getattr(n, "keywords", set())}
      if kws.intersection({k.lower() for k in PUBLIC_OPINION_KEYWORDS}):
        filtered.append(n)
    
    if filtered:
      parts.append("【线下舆论】")
      for n in filtered[:max_public_opinion]:
        parts.append(str(n.description))
  
  # 2. 线上舆论（从舆论库中读取）
  try:
    online_opinions = get_online_opinions_for_experts(
      since_hours=24,
      sim_folder=sim_folder,
      curr_time=curr_time
    )
    if online_opinions and "没有网民发言" not in online_opinions:
      parts.append("\n【线上舆论】")
      parts.append(online_opinions)
  except Exception as e:
    print(f"[Expert] 读取线上舆论失败: {e}")
  
  if not parts:
    return "(当前尚未形成明确的公众舆论摘要)"
  
  return "\n".join(parts)


def expert_meeting_speech(persona,
                          question: str,
                          max_memories: int = 6,
                          max_rules: int = 3,
                          max_case_snippets: int = 3,
                          max_public_opinion: int = 1,
                          max_web_results: int = 3,
                          meeting_time: datetime.datetime = None) -> str:
  """Generate an in-simulation expert speech for a meeting.

  The speech is grounded in:
  - retrieved long-term memories (including seeded cases and public opinion),
  - local food poisoning case knowledge paragraphs,
  - structured food safety rules (FS001–FS120),
  - Tavily web search results for real-time information.
  
  Args:
    meeting_time: 会议时间，用于限制记忆检索到过去24小时内
  """

  if not question or not question.strip():
    return "(empty question)"

  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Expert")

  memory_nodes = _select_relevant_memory_nodes(persona, question, max_memories, meeting_time)
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
    curr_time=meeting_time,
  )

  # Tavily 联网搜索：获取最新的公共卫生/食品安全相关信息
  web_query = f"校园食物中毒 食品安全 {question[:50]}"
  web_snippets = tavily_search_snippets(web_query, max_results=max_web_results)
  if web_snippets:
    web_block = "\n\n".join(web_snippets)
  else:
    web_block = "(联网搜索暂无返回结果)"

  # 构建思考依据（用于调试和显示）- 保存完整内容
  global _last_expert_reasoning
  _last_expert_reasoning = {
    "memory": memory_block,
    "case_knowledge": case_block,
    "rules": rules_block,
    "public_opinion": opinion_block,
    "web_search": web_block,
  }
  
  # 打印思考过程日志
  print(f"\n{'='*60}")
  print(f"[思考过程] {name} 正在准备发言...")
  print(f"{'='*60}")
  print(f"📝 长期记忆检索结果:\n{memory_block[:500]}..." if len(memory_block) > 500 else f"📝 长期记忆:\n{memory_block}")
  print(f"\n📚 案例知识库:\n{case_block[:300]}..." if len(case_block) > 300 else f"\n📚 案例知识库:\n{case_block}")
  print(f"\n📋 规则库:\n{rules_block[:300]}..." if len(rules_block) > 300 else f"\n📋 规则库:\n{rules_block}")
  print(f"\n👥 公众舆论:\n{opinion_block[:200]}..." if len(opinion_block) > 200 else f"\n👥 公众舆论:\n{opinion_block}")
  print(f"\n🌐 网络搜索:\n{web_block[:300]}..." if len(web_block) > 300 else f"\n🌐 网络搜索:\n{web_block}")
  print(f"{'='*60}\n")

  prompt = (
    f'你是一名公共卫生与食品安全领域的资深专家，目前正在参加一次围绕"校园食物中毒/食品安全"的专家咨询会议。'
    f'请基于下列信息进行分析和发言：\n\n'
    f'【一、你在当前世界线中的长期记忆片段】（只列出若干最相关的）\n'
    f'{memory_block}\n\n'
    f'【二、以往校园食物中毒案例的本地知识片段】\n'
    f'{case_block}\n\n'
    f'【三、结构化食品安全规则库条文】（带编号，可在回答中引用）\n'
    f'{rules_block}\n\n'
    f'【四、社会公众舆论与家长关切摘要】\n'
    f'{opinion_block}\n\n'
    f'【五、联网搜索获取的最新相关信息】\n'
    f'{web_block}\n\n'
    f'【六、本轮会议主持人交给你的具体问题】\n'
    f'{question.strip()}\n\n'
    f'请你以"{name}"的身份，用简洁的中文，给出一段面向"主持人和其他与会者"的发言，要求：\n'
    f'1. 先简要指出你从长期记忆和以往案例中联想到的关键点（如制度缺陷、监管薄弱环节、信息透明度等），必要时可以引用 FS 规则编号（例如"根据 FS012..."）。\n'
    f'2. 如果联网搜索有相关信息，可以引用最新的案例或政策动态。\n'
    f'3. 分析当前事件在健康风险、学校运行和社会舆论方面的主要风险点。\n'
    f'4. 给出对学校、监管部门和家长分别的操作性建议，明确哪些是"立刻要做的"、哪些是"中长期需要改进的制度"。\n'
    f'5. 全程保持专业、克制，但对受害学生和家长表达同理心，避免过度技术化或冷漠表述。\n'
  )

  return ChatGPT_single_request(prompt)


def market_supervision_expert_meeting_speech(persona,
                                              question: str,
                                              max_memories: int = 6,
                                              max_rules: int = 3,
                                              max_case_snippets: int = 3,
                                              max_public_opinion: int = 1,
                                              max_web_results: int = 3,
                                              meeting_time: datetime.datetime = None) -> str:
  """Generate speech for Market Supervision Expert."""
  if not question or not question.strip():
    return "(empty question)"

  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Market Supervision Expert")

  memory_nodes = _select_relevant_memory_nodes(persona, question, max_memories, meeting_time)
  memory_block = _format_memory_nodes_for_prompt(memory_nodes)

  case_snippets = retrieve_food_poisoning_knowledge(question, top_k=max_case_snippets)
  case_block = "\n\n".join(case_snippets) if case_snippets else "(暂无相关案例)"

  rules = retrieve_market_supervision_rules(question, top_k=max_rules)
  rules_block = format_market_supervision_rules_for_prompt(rules)

  opinion_block = _format_public_opinion_from_nodes(memory_nodes, max_public_opinion, curr_time=meeting_time)

  # Tavily 联网搜索：获取最新的市场监管相关信息
  web_query = f"市场监管 食品安全 学校食堂 {question[:50]}"
  web_snippets = tavily_search_snippets(web_query, max_results=max_web_results)
  if web_snippets:
    web_block = "\n\n".join(web_snippets)
  else:
    web_block = "(联网搜索暂无返回结果)"

  # 保存思考过程到全局变量 - 保存完整内容
  global _last_expert_reasoning
  _last_expert_reasoning = {
    "memory": memory_block,
    "case_knowledge": case_block,
    "rules": rules_block,
    "public_opinion": opinion_block,
    "web_search": web_block,
  }

  # 打印思考过程日志
  print(f"\n{'='*60}")
  print(f"[思考过程] {name} (市场监管专家) 正在准备发言...")
  print(f"{'='*60}")
  print(f"📝 长期记忆:\n{memory_block[:400]}..." if len(memory_block) > 400 else f"📝 长期记忆:\n{memory_block}")
  print(f"\n📚 案例知识库:\n{case_block[:300]}..." if len(case_block) > 300 else f"\n📚 案例知识库:\n{case_block}")
  print(f"\n📋 市场监管规则库:\n{rules_block[:300]}..." if len(rules_block) > 300 else f"\n📋 规则库:\n{rules_block}")
  print(f"\n🌐 网络搜索:\n{web_block[:300]}..." if len(web_block) > 300 else f"\n🌐 网络搜索:\n{web_block}")
  print(f"{'='*60}\n")

  prompt = (
    "你是一名市场监管领域的资深专家，正在参加校园食品安全专家咨询会议。"
    "你的专业领域包括：市场主体监管、食品经营许可、价格监管、消费者权益保护等。\n"
    "请基于下列信息进行分析和发言：\n\n"
    "【一、长期记忆片段】\n"
    f"{memory_block}\n\n"
    "【二、历史案例】\n"
    f"{case_block}\n\n"
    "【三、市场监管规则库】\n"
    f"{rules_block}\n\n"
    "【四、公众舆论】\n"
    f"{opinion_block}\n\n"
    "【五、联网搜索获取的最新相关信息】\n"
    f"{web_block}\n\n"
    "【六、本轮问题】\n"
    f"{question.strip()}\n\n"
    f"请以 {name} 的身份发言，要求：\n"
    "1. 从市场监管角度分析食堂经营资质、供应商审核、价格行为等问题。\n"
    "2. 如果联网搜索有相关信息，可以引用最新的监管政策或案例。\n"
    "3. 分析市场监管责任主体和监管漏洞。\n"
    "4. 给出操作性建议，区分紧急措施和长期制度完善。\n"
    "5. 可引用 MS 规则编号，保持专业客观。\n"
  )
  return ChatGPT_single_request(prompt)


def education_expert_meeting_speech(persona,
                                     question: str,
                                     max_memories: int = 6,
                                     max_rules: int = 3,
                                     max_case_snippets: int = 3,
                                     max_public_opinion: int = 1,
                                     max_web_results: int = 3,
                                     meeting_time: datetime.datetime = None) -> str:
  """Generate speech for Education Bureau Representative."""
  if not question or not question.strip():
    return "(empty question)"

  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Education Bureau Representative")

  memory_nodes = _select_relevant_memory_nodes(persona, question, max_memories, meeting_time)
  memory_block = _format_memory_nodes_for_prompt(memory_nodes)

  case_snippets = retrieve_food_poisoning_knowledge(question, top_k=max_case_snippets)
  case_block = "\n\n".join(case_snippets) if case_snippets else "(暂无相关案例)"

  rules = retrieve_education_rules(question, top_k=max_rules)
  rules_block = format_education_rules_for_prompt(rules)

  opinion_block = _format_public_opinion_from_nodes(memory_nodes, max_public_opinion, curr_time=meeting_time)

  # Tavily 联网搜索：获取最新的校园安全/教育管理相关信息
  web_query = f"教育局 学校食堂管理 校园安全 {question[:50]}"
  web_snippets = tavily_search_snippets(web_query, max_results=max_web_results)
  if web_snippets:
    web_block = "\n\n".join(web_snippets)
  else:
    web_block = "(联网搜索暂无返回结果)"

  # 保存思考过程到全局变量 - 保存完整内容
  global _last_expert_reasoning
  _last_expert_reasoning = {
    "memory": memory_block,
    "case_knowledge": case_block,
    "rules": rules_block,
    "public_opinion": opinion_block,
    "web_search": web_block,
  }

  # 打印思考过程日志
  print(f"\n{'='*60}")
  print(f"[思考过程] {name} (教育局代表) 正在准备发言...")
  print(f"{'='*60}")
  print(f"📝 长期记忆:\n{memory_block[:400]}..." if len(memory_block) > 400 else f"📝 长期记忆:\n{memory_block}")
  print(f"\n📚 案例知识库:\n{case_block[:300]}..." if len(case_block) > 300 else f"\n📚 案例知识库:\n{case_block}")
  print(f"\n📋 教育管理规则库:\n{rules_block[:300]}..." if len(rules_block) > 300 else f"\n📋 规则库:\n{rules_block}")
  print(f"\n🌐 网络搜索:\n{web_block[:300]}..." if len(web_block) > 300 else f"\n🌐 网络搜索:\n{web_block}")
  print(f"{'='*60}\n")

  prompt = (
    "你是一名教育局的资深代表，正在参加校园食品安全专家咨询会议。"
    "你的专业领域包括：学校管理、校园安全、家校沟通、应急处置、教育政策执行等。\n"
    "请基于下列信息进行分析和发言：\n\n"
    "【一、长期记忆片段】\n"
    f"{memory_block}\n\n"
    "【二、历史案例】\n"
    f"{case_block}\n\n"
    "【三、教育管理规则库】\n"
    f"{rules_block}\n\n"
    "【四、公众舆论】\n"
    f"{opinion_block}\n\n"
    "【五、联网搜索获取的最新相关信息】\n"
    f"{web_block}\n\n"
    "【六、本轮问题】\n"
    f"{question.strip()}\n\n"
    f"请以 {name} 的身份发言，要求：\n"
    "1. 从教育管理角度分析学校管理责任、应急预案执行、家校沟通机制等。\n"
    "2. 如果联网搜索有相关信息，可以引用最新的教育政策或案例。\n"
    "3. 分析事件对教学秩序、学生心理、家长信任的影响。\n"
    "4. 给出操作性建议，区分紧急措施和长期制度完善。\n"
    "5. 可引用 ED 规则编号，对受影响学生和家长表达关怀。\n"
  )
  return ChatGPT_single_request(prompt)


def get_expert_role(persona) -> str:
  """Get the expert role type from persona name."""
  try:
    role = getattr(persona.scratch, "role", None)
    if role:
      return role
    name = persona.name.lower()
    if "market" in name or "supervision" in name:
      return "market_supervision_expert"
    elif "education" in name:
      return "education_expert"
    elif "health" in name or "food" in name:
      return "public_health_expert"
    else:
      return "generic_expert"
  except Exception:
    return "generic_expert"


def get_expert_speech_function(persona):
  """Return the appropriate speech function for an expert persona."""
  role = get_expert_role(persona)
  if role == "market_supervision_expert":
    return market_supervision_expert_meeting_speech
  elif role == "education_expert":
    return education_expert_meeting_speech
  else:
    return expert_meeting_speech


# ========== 主持人逻辑 ==========

def _is_moderator_persona(persona) -> bool:
  """判断一个 persona 是否是主持人。"""
  try:
    name = persona.name.lower()
    return "moderator" in name or "主持" in name
  except Exception:
    return False


def moderator_opening_speech(persona,
                              topic: str,
                              expert_names: List[str],
                              first_expert_name: str = "",
                              max_memories: int = 4,
                              max_case_snippets: int = 2,
                              max_rules: int = 3,
                              max_public_opinion: int = 1,
                              meeting_time: datetime.datetime = None) -> str:
  """主持人开场白：介绍会议背景、与会专家、议程规则、并引导第一位专家发言。"""
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  memory_nodes = _select_relevant_memory_nodes(persona, topic, max_memories, meeting_time)
  memory_block = _format_memory_nodes_for_prompt(memory_nodes)

  case_snippets = retrieve_food_poisoning_knowledge(topic, top_k=max_case_snippets)
  case_block = "\n\n".join(case_snippets) if case_snippets else "(暂无相关案例)"

  rules = retrieve_moderator_rules(topic, top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  opinion_block = _format_public_opinion_from_nodes(memory_nodes, max_public_opinion=1, curr_time=meeting_time)

  experts_str = "、".join(expert_names) if expert_names else "各位专家"
  first_expert_hint = f"\n\n【首位发言专家】\n{first_expert_name}" if first_expert_name else ""

  prompt = (
    "你是一名专业的会议主持人，正在主持一场关于校园食品安全的专家咨询会议。\n"
    "当前时间是晚上11点（23:00），这是一场晚间紧急会议。\n"
    "请基于下列信息进行开场发言：\n\n"
    "【一、长期记忆片段】\n"
    f"{memory_block}\n\n"
    "【二、历史案例】\n"
    f"{case_block}\n\n"
    "【三、主持人规则库】\n"
    f"{rules_block}\n\n"
    "【四、公众舆论】\n"
    f"{opinion_block}\n\n"
    "【五、会议主题】\n"
    f"{topic.strip()}\n\n"
    "【六、与会专家】\n"
    f"{experts_str}"
    f"{first_expert_hint}\n\n"
    f"请以 {name} 的身份进行一段完整的开场发言，要求：\n"
    "1. 简要介绍会议背景和目的。\n"
    "2. 介绍与会专家（可引用 MR 规则编号强调主持原则）。\n"
    "3. 说明本轮讨论的重点和议程安排。\n"
    "4. 最后，向第一位发言专家提出具体问题，引导其开始发言。\n"
    "5. 保持中立、专业、有条理的主持风格，整体篇幅控制在一段话内。\n"
  )
  return ChatGPT_single_request(prompt)


def moderator_question_speech(persona,
                               round_num: int,
                               previous_speeches: List[Dict[str, str]],
                               next_expert_name: str,
                               topic: str,
                               max_rules: int = 3) -> str:
  """主持人提问/引导发言：决定下一个发言专家，提出针对性问题。"""
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  rules = retrieve_moderator_rules(topic, top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  # 格式化之前的发言
  prev_speeches_text = ""
  if previous_speeches:
    for sp in previous_speeches:
      prev_speeches_text += f"【{sp.get('speaker', '专家')}】:\n{sp.get('content', '')}\n\n"
  else:
    prev_speeches_text = "(尚无专家发言)"

  prompt = (
    "你是一名专业的会议主持人，正在主持校园食品安全专家咨询会议。\n"
    f"现在是第 {round_num} 轮讨论，请引导下一位专家发言。\n\n"
    "【主持人规则库】\n"
    f"{rules_block}\n\n"
    "【之前专家的发言】\n"
    f"{prev_speeches_text}\n"
    "【会议主题】\n"
    f"{topic.strip()}\n\n"
    "【下一位发言专家】\n"
    f"{next_expert_name}\n\n"
    f"请以 {name} 的身份：\n"
    "1. 简要总结之前专家的关键观点（如有）。\n"
    "2. 指出需要进一步讨论的问题或分歧点。\n"
    "3. 向下一位专家提出具体的问题，引导其发言。\n"
    "4. 问题应与该专家的专业领域相关。\n"
  )
  return ChatGPT_single_request(prompt)


def moderator_decide_speaking_order(persona,
                                     topic: str,
                                     expert_names: List[str],
                                     expert_roles: List[str],
                                     round_num: int = 1,
                                     previous_round_summary: str = "",
                                     max_rules: int = 3) -> List[str]:
  """主持人根据议题动态决定本轮专家发言顺序。
  
  返回：按发言顺序排列的专家名字列表
  """
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  rules = retrieve_moderator_rules("发言顺序 议程安排", top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  # 构建专家信息
  expert_info = ""
  for i, (ename, erole) in enumerate(zip(expert_names, expert_roles)):
    role_desc = {
      "public_health_expert": "公共卫生专家 - 负责健康风险分析、流行病学调查",
      "market_supervision_expert": "市场监管专家 - 负责执法、责任认定、市场规范",
      "education_expert": "教育局代表 - 负责学校管理、制度建设、家校沟通"
    }.get(erole, erole)
    expert_info += f"{i+1}. {ename}（{role_desc}）\n"

  prev_context = ""
  if previous_round_summary:
    prev_context = f"【上一轮讨论总结】\n{previous_round_summary}\n\n"

  prompt = (
    "你是一名专业的会议主持人，正在主持校园食品安全专家咨询会议。\n"
    f"现在需要决定第 {round_num} 轮的专家发言顺序。\n\n"
    "【主持人规则库】\n"
    f"{rules_block}\n\n"
    f"{prev_context}"
    "【会议主题】\n"
    f"{topic.strip()}\n\n"
    "【与会专家】\n"
    f"{expert_info}\n"
    f"请以 {name} 的身份，根据议题特点和专家专业领域，决定本轮发言顺序。\n"
    "要求：\n"
    "1. 考虑议题的逻辑顺序（如：先溯源分析、再责任认定、最后制度建设）\n"
    "2. 考虑专家之间的互补性和衔接性\n"
    "3. 如有上轮总结，根据待深入问题调整顺序\n\n"
    "请只输出专家名字，用逗号分隔，按发言顺序排列。例如：张三,李四,王五\n"
    "不要输出任何解释，只输出名字序列。"
  )
  
  result = ChatGPT_single_request(prompt)
  
  # 解析返回的顺序
  try:
    ordered_names = [n.strip() for n in result.strip().split(",") if n.strip()]
    # 验证返回的名字都在专家列表中
    valid_names = [n for n in ordered_names if n in expert_names]
    # 补充遗漏的专家
    for n in expert_names:
      if n not in valid_names:
        valid_names.append(n)
    return valid_names
  except Exception:
    # 解析失败，返回原顺序
    return expert_names


def moderator_feedback_to_expert(persona,
                                  expert_name: str,
                                  expert_speech: str,
                                  expert_role: str,
                                  previous_speeches: List[Dict[str, str]],
                                  topic: str,
                                  max_rules: int = 2) -> str:
  """主持人对单个专家发言的即时反馈。
  
  针对专家发言给出：
  1. 肯定有价值的观点
  2. 提出追问或补充问题
  3. 关联之前专家的观点
  """
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  rules = retrieve_moderator_rules("反馈 追问 引导", top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  # 格式化之前的发言
  prev_context = ""
  if previous_speeches:
    prev_context = "【之前专家的发言要点】\n"
    for sp in previous_speeches[-3:]:  # 只取最近3条
      prev_context += f"- {sp.get('speaker', '专家')}: {sp.get('content', '')[:200]}...\n"
    prev_context += "\n"

  role_desc = {
    "public_health_expert": "公共卫生专家",
    "market_supervision_expert": "市场监管专家",
    "education_expert": "教育局代表"
  }.get(expert_role, expert_role)

  prompt = (
    "你是一名专业的会议主持人，正在主持校园食品安全专家咨询会议。\n"
    f"刚才 {expert_name}（{role_desc}）完成了发言，请给出即时反馈。\n\n"
    "【主持人规则库】\n"
    f"{rules_block}\n\n"
    f"{prev_context}"
    "【会议主题】\n"
    f"{topic.strip()}\n\n"
    f"【{expert_name} 的发言】\n"
    f"{expert_speech}\n\n"
    f"请以 {name} 的身份给出简短反馈（100-200字），要求：\n"
    "1. 肯定该专家发言中最有价值的1-2个观点。\n"
    "2. 如果有疑问或需要补充的地方，提出1个简短追问。\n"
    "3. 如果能与之前专家的观点形成呼应或对比，简要指出。\n"
    "4. 语气专业、简洁，为下一位专家发言做过渡。\n"
  )
  return ChatGPT_single_request(prompt)


def moderator_targeted_advice(persona,
                               target_expert_name: str,
                               target_expert_role: str,
                               target_expert_speech: str,
                               all_speeches: List[Dict[str, str]],
                               topic: str,
                               round_num: int,
                               max_rules: int = 2) -> str:
  """主持人在一轮结束后，综合所有专家发言，对特定专家给出针对性意见和下一步聚焦点。
  
  这个函数在所有专家都发言完、主持人总结后调用。
  """
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  rules = retrieve_moderator_rules("引导 聚焦 建议", top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  # 格式化其他专家的发言
  other_speeches_text = ""
  for sp in all_speeches:
    if sp.get("speaker") != target_expert_name:
      other_speeches_text += f"【{sp.get('speaker', '专家')}】:\n{sp.get('content', '')[:400]}...\n\n"

  role_desc = {
    "public_health_expert": "公共卫生专家",
    "market_supervision_expert": "市场监管专家",
    "education_expert": "教育局代表"
  }.get(target_expert_role, target_expert_role)

  prompt = (
    "你是一名专业的会议主持人，正在主持校园食品安全专家咨询会议。\n"
    f"第 {round_num} 轮讨论已结束，现在需要对 {target_expert_name}（{role_desc}）提出针对性意见。\n\n"
    "【主持人规则库】\n"
    f"{rules_block}\n\n"
    "【会议主题】\n"
    f"{topic.strip()}\n\n"
    f"【{target_expert_name} 本轮的发言】\n"
    f"{target_expert_speech}\n\n"
    "【其他专家的发言】\n"
    f"{other_speeches_text}\n"
    f"请以 {name} 的身份，对 {target_expert_name} 提出针对性意见（150-250字），要求：\n"
    "1. 结合其他专家的观点，指出该专家发言中可以补充或深化的地方。\n"
    "2. 提出该专家在下一轮讨论中应聚焦的具体问题或方向。\n"
    "3. 如果该专家的观点与其他专家有分歧，指出并提出协调建议。\n"
    "4. 语气专业、建设性，帮助该专家在下一轮提供更有价值的意见。\n"
  )
  return ChatGPT_single_request(prompt)


def moderator_round_summary(persona,
                             round_num: int,
                             round_speeches: List[Dict[str, str]],
                             topic: str,
                             max_rules: int = 3,
                             max_memories: int = 4,
                             max_public_opinion: int = 1,
                             meeting_time: datetime.datetime = None) -> str:
  """主持人轮次总结：总结本轮所有专家发言，提炼共识和分歧。"""
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  # 检索主持人的长期记忆（包括平民舆论），限制在过去24小时内
  memory_nodes = _select_relevant_memory_nodes(persona, topic, max_memories, meeting_time)
  memory_block = _format_memory_nodes_for_prompt(memory_nodes)
  
  # 检索公众舆论（从平民对话中收集）
  opinion_block = _format_public_opinion_from_nodes(memory_nodes, max_public_opinion, curr_time=meeting_time)

  rules = retrieve_moderator_rules("总结 归纳 共识", top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  # 格式化本轮发言（完整版）
  speeches_text = ""
  for sp in round_speeches:
    speeches_text += f"【{sp.get('speaker', '专家')}】:\n{sp.get('content', '')}\n\n"

  # 保存思考过程到全局变量（供前端显示）
  global _last_expert_reasoning
  _last_expert_reasoning = {
    "memory": memory_block,
    "expert_speeches": speeches_text,
    "rules": rules_block,
    "public_opinion": opinion_block,
  }
  
  # 打印思考过程日志
  print(f"\n{'='*60}")
  print(f"[思考过程] 主持人正在总结第 {round_num} 轮讨论...")
  print(f"{'='*60}")
  print(f"📝 长期记忆:\n{memory_block[:400]}..." if len(memory_block) > 400 else f"📝 长期记忆:\n{memory_block}")
  print(f"\n💬 本轮专家发言:\n{speeches_text[:800]}..." if len(speeches_text) > 800 else f"\n� 本轮专家发言:\n{speeches_text}")
  print(f"\n📋 主持人规则库:\n{rules_block[:300]}..." if len(rules_block) > 300 else f"\n📋 主持人规则库:\n{rules_block}")
  print(f"\n👥 公众舆论:\n{opinion_block[:300]}..." if len(opinion_block) > 300 else f"\n👥 公众舆论:\n{opinion_block}")
  print(f"{'='*60}\n")

  prompt = (
    "你是一名专业的会议主持人，正在主持校园食品安全专家咨询会议。\n"
    f"第 {round_num} 轮讨论已结束，请进行本轮总结。\n\n"
    "【一、长期记忆片段】\n"
    f"{memory_block}\n\n"
    "【二、主持人规则库】\n"
    f"{rules_block}\n\n"
    "【三、公众舆论（平民对话摘要）】\n"
    f"{opinion_block}\n\n"
    "【四、本轮专家发言】\n"
    f"{speeches_text}\n"
    "【五、会议主题】\n"
    f"{topic.strip()}\n\n"
    f"请以 {name} 的身份进行本轮总结，要求：\n"
    "1. 提炼各专家发言的核心观点。\n"
    "2. 明确指出专家之间的共识点。\n"
    "3. 如实反映专家之间的分歧。\n"
    "4. 结合公众舆论，总结本轮讨论形成的可操作建议。\n"
    "5. 为下一轮讨论提出引导性问题（如有）。\n"
  )
  return ChatGPT_single_request(prompt)


def moderator_final_summary_and_decision(persona,
                                          round_speeches: List[Dict[str, str]],
                                          all_round_summaries: List[str],
                                          topic: str,
                                          max_rules: int = 3,
                                          max_memories: int = 4,
                                          meeting_time: datetime.datetime = None) -> str:
  """主持人最终总结与决策（用于最后一轮）。
  
  与普通轮次总结不同，这个函数会：
  1. 总结本轮（第三轮）讨论要点
  2. 回顾并整合前两轮总结
  3. 形成完整的会议结论
  4. 提出明确的最终决策和行动建议
  
  不会再提"下一轮讨论"。
  """
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  # 检索记忆（过去24小时）
  memory_nodes = _select_relevant_memory_nodes(persona, topic, max_memories, meeting_time)
  memory_block = _format_memory_nodes_for_prompt(memory_nodes)
  
  # 公众舆论
  opinion_block = _format_public_opinion_from_nodes(memory_nodes, max_public_opinion=1, curr_time=meeting_time)

  rules = retrieve_moderator_rules("总结 决策 结论", top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  # 格式化本轮发言（完整版）
  current_round_text = ""
  for sp in round_speeches:
    current_round_text += f"【{sp.get('speaker', '专家')}】:\n{sp.get('content', '')}\n\n"

  # 格式化前几轮总结
  previous_summaries_text = ""
  for i, summary in enumerate(all_round_summaries, 1):
    previous_summaries_text += f"【第{i}轮总结】\n{summary}\n\n"

  # 保存思考过程到全局变量（供前端显示）
  global _last_expert_reasoning
  _last_expert_reasoning = {
    "memory": memory_block,
    "previous_summaries": previous_summaries_text,
    "current_round_speeches": current_round_text,
    "rules": rules_block,
    "public_opinion": opinion_block,
  }
  
  # 打印思考过程日志
  print(f"\n{'='*60}")
  print(f"[思考过程] 主持人正在生成最终总结与决策...")
  print(f"{'='*60}")
  print(f"📝 长期记忆:\n{memory_block[:300]}..." if len(memory_block) > 300 else f"📝 长期记忆:\n{memory_block}")
  print(f"\n📋 前几轮总结:\n{previous_summaries_text[:500]}..." if len(previous_summaries_text) > 500 else f"\n📋 前几轮总结:\n{previous_summaries_text}")
  print(f"\n💬 本轮发言:\n{current_round_text[:500]}..." if len(current_round_text) > 500 else f"\n💬 本轮发言:\n{current_round_text}")
  print(f"{'='*60}\n")

  prompt = (
    "你是一名专业的会议主持人，正在主持校园食品安全专家咨询会议。\n"
    "这是本次会议的**最后一轮**讨论，你需要做出最终总结和决策，**不要再提下一轮讨论**。\n"
    "当前时间是晚上11点（23:00），这是一场晚间紧急会议。\n\n"
    "【一、长期记忆片段】\n"
    f"{memory_block}\n\n"
    "【二、主持人规则库】\n"
    f"{rules_block}\n\n"
    "【三、公众舆论（平民对话摘要）】\n"
    f"{opinion_block}\n\n"
    "【四、前几轮讨论总结（你之前的总结）】\n"
    f"{previous_summaries_text}\n"
    "【五、本轮（最后一轮）专家发言】\n"
    f"{current_round_text}\n"
    "【六、会议主题】\n"
    f"{topic.strip()}\n\n"
    f"请以 {name} 的身份，完成以下内容（这是最终总结，不要再提下一轮）：\n\n"
    "## 一、本轮讨论要点\n"
    "简要总结本轮（最后一轮）各专家的核心观点。\n\n"
    "## 二、全程会议回顾\n"
    "整合三轮讨论的主要成果，归纳专家共识和分歧。\n\n"
    "## 三、最终决策与行动建议\n"
    "基于全部讨论，提出明确的、可操作的最终决策，包括：\n"
    "1. **立即行动**（24-48小时内必须完成）\n"
    "2. **短期措施**（1-2周内落实）\n"
    "3. **长期制度建设**（1-3个月内推进）\n\n"
    "## 四、责任分工\n"
    "明确各部门（卫健、市场监管、教育）的具体责任。\n\n"
    "## 五、结语\n"
    "简短的会议闭幕语，感谢各位专家，宣布会议结束。\n\n"
    "要求：语气专业、结论明确、行动清晰，体现最终决策的权威性。"
  )
  return ChatGPT_single_request(prompt)


def extract_decision_for_civilians(final_decision: str, topic: str) -> str:
  """从专家会议最终决策中提取客观政策通报。
  
  注意：只提取客观的政策内容，不预先分析影响。
  让平民agent自己理解和讨论这些政策对自己的影响，这样更真实。
  """
  if not final_decision:
    return ""
  
  prompt = (
    "你是一名政务信息发布官员。请将以下专家会议决策转换为面向公众的官方通报。\n\n"
    f"【原始决策】\n{final_decision[:3000]}\n\n"
    "请按以下格式输出（控制在200字以内）：\n\n"
    "【关于校园食品安全事件的处置通报】\n\n"
    "一、事件概况：（一句话客观描述）\n\n"
    "二、已采取措施：\n"
    "  - （列出3-4条已实施的措施）\n\n"
    "三、后续安排：\n"
    "  - （时间表和下一步计划）\n\n"
    "四、咨询渠道：\n"
    "  - （投诉电话等）\n\n"
    "要求：\n"
    "1. 只陈述客观事实和政策，不要分析'对谁有什么影响'\n"
    "2. 语言正式但通俗，像政府公告\n"
    "3. 不要说教或建议市民做什么"
  )
  
  try:
    civilian_version = ChatGPT_single_request(prompt)
    return civilian_version if civilian_version else ""
  except Exception as e:
    print(f"[Decision] 提取平民版决策失败: {e}")
    return ""


def broadcast_decision_to_civilians(personas: Dict[str, "Persona"],
                                     decision_summary: str,
                                     topic: str,
                                     created_time: datetime.datetime) -> None:
  """将决策摘要写入所有非专家平民的记忆。
  
  这样平民可以在后续对话中讨论和分析决策对自己的影响。
  """
  if not decision_summary:
    return
  
  print(f"[Decision] 正在将决策通报写入平民记忆...")
  
  civilian_count = 0
  for name, persona in personas.items():
    # 跳过专家和主持人
    if _is_expert_persona(persona) or _is_moderator_persona(persona):
      continue
    
    try:
      expiration = None
      s = "校园食品安全专家会议决策"
      p = "影响"
      o = "学校食堂和家长"
      description = decision_summary
      keywords = {"专家会议决策", "食品安全", "校园", "家长", "学生", "食堂"}
      poignancy = 0.85  # 高重要性
      embedding_key = f"expert_meeting_decision_{created_time.strftime('%Y%m%d')}"
      embedding_vec = get_embedding(description[:500])
      embedding_pair = (embedding_key, embedding_vec)
      filling: List = []
      
      persona.a_mem.add_event(
        created=created_time,
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
      civilian_count += 1
    except Exception as e:
      print(f"[Decision] 写入 {name} 记忆失败: {e}")
      continue
  
  print(f"[Decision] 决策通报已写入 {civilian_count} 个平民的记忆")


def moderator_summary_with_advice(persona,
                                   round_num: int,
                                   round_speeches: List[Dict[str, str]],
                                   expert_names: List[str],
                                   expert_roles: List[str],
                                   topic: str,
                                   max_rules: int = 3) -> str:
  """主持人轮次总结 + 对每位专家的意见（合并为一段话）。
  
  返回一段话，包含：
  1. 本轮总结
  2. 对每位专家的针对性意见
  """
  try:
    name = getattr(persona.scratch, "name", persona.name)
  except Exception:
    name = getattr(persona, "name", "Meeting Moderator")

  rules = retrieve_moderator_rules("总结 归纳 建议", top_k=max_rules)
  rules_block = format_moderator_rules_for_prompt(rules)

  # 格式化本轮发言
  speeches_text = ""
  for sp in round_speeches:
    speeches_text += f"【{sp.get('speaker', '专家')}】:\n{sp.get('content', '')}\n\n"

  # 专家信息
  expert_info = ""
  for ename, erole in zip(expert_names, expert_roles):
    role_desc = {
      "public_health_expert": "公共卫生专家",
      "market_supervision_expert": "市场监管专家",
      "education_expert": "教育局代表"
    }.get(erole, erole)
    expert_info += f"- {ename}（{role_desc}）\n"

  prompt = (
    "你是一名专业的会议主持人，正在主持校园食品安全专家咨询会议。\n"
    f"第 {round_num} 轮讨论已结束，请进行总结并对每位专家提出意见。\n\n"
    "【主持人规则库】\n"
    f"{rules_block}\n\n"
    "【本轮专家发言】\n"
    f"{speeches_text}\n"
    "【与会专家】\n"
    f"{expert_info}\n"
    "【会议主题】\n"
    f"{topic.strip()}\n\n"
    f"请以 {name} 的身份，用一段连贯的话完成以下内容：\n"
    "1. 首先总结本轮讨论的核心观点和共识（2-3句）。\n"
    "2. 然后依次对每位专家提出简短的针对性意见（每人1-2句），指出下一轮应聚焦的方向。\n"
    "3. 最后提出下一轮的引导性问题。\n"
    "4. 整体控制在300字以内，语气专业简洁。\n"
  )
  return ChatGPT_single_request(prompt)


def extract_speech_key_points(speaker_name: str, 
                               speaker_role: str,
                               speech_content: str,
                               topic: str) -> str:
  """从专家发言中提取核心要点，用于写入记忆。
  
  Args:
    speaker_name: 发言者名字
    speaker_role: 发言者角色（如"公共卫生专家"）
    speech_content: 完整发言内容
    topic: 会议主题
    
  Returns:
    格式化的要点摘要（约150-200字）
  """
  if not speech_content or len(speech_content) < 50:
    return speech_content
  
  role_desc = {
    "public_health_expert": "公共卫生专家",
    "market_supervision_expert": "市场监管专家", 
    "education_expert": "教育局代表",
    "moderator": "主持人"
  }.get(speaker_role, speaker_role)
  
  prompt = (
    f"请从以下{role_desc}的发言中提取核心要点，用于存入记忆系统。\n\n"
    f"【发言者】{speaker_name}（{role_desc}）\n"
    f"【会议主题】{topic}\n"
    f"【原始发言】\n{speech_content}\n\n"
    "请按以下格式提取要点（控制在150-200字）：\n"
    f"【{speaker_name}核心观点】\n"
    "1. 根源判断：（一句话概括其对问题根源的判断）\n"
    "2. 主要建议：（列出2-3条最重要的建议）\n"
    "3. 关键立场：（其与其他专家可能的共识或分歧点）\n"
  )
  
  try:
    key_points = ChatGPT_single_request(prompt)
    return key_points if key_points else speech_content[:300]
  except Exception as e:
    print(f"[Memory] 提取要点失败: {e}")
    return speech_content[:300] + "..."


def write_meeting_memory(persona,
                          content: str,
                          memory_type: str,
                          topic: str,
                          round_num: int,
                          created_time: datetime.datetime,
                          speaker_name: str = "") -> bool:
  """将会议内容写入单个角色的长期记忆。
  
  Args:
    persona: 要写入记忆的角色
    content: 记忆内容
    memory_type: 记忆类型 - "summary"(总结), "expert_speech"(专家发言), "opening"(开场)
    topic: 会议主题
    round_num: 轮次号
    created_time: 创建时间
    speaker_name: 发言者名字（用于专家发言）
  """
  if not content:
    return False
    
  try:
    created = created_time
    expiration = None
    
    # 根据类型设置不同的记忆标签
    if memory_type == "summary":
      s = f"第{round_num}轮会议总结"
      keywords = {"会议总结", "专家讨论", f"第{round_num}轮", "食品安全"}
      poignancy = 0.8
    elif memory_type == "expert_speech":
      s = f"{speaker_name}在第{round_num}轮的发言"
      keywords = {"专家发言", speaker_name, f"第{round_num}轮", "食品安全"}
      poignancy = 0.7
    elif memory_type == "opening":
      s = "会议开场"
      keywords = {"会议开场", "专家会议", "食品安全"}
      poignancy = 0.6
    else:
      s = f"会议记录-{memory_type}"
      keywords = {"会议", "食品安全"}
      poignancy = 0.5
    
    p = "关于"
    o = topic[:30] if topic else "食品安全议题"
    description = content
    embedding_key = f"meeting_{memory_type}_{round_num}_{speaker_name}"
    embedding_vec = get_embedding(description[:500])  # 限制嵌入长度
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
    print(f"[Meeting] {memory_type} 已写入 {persona.name} 的记忆")
    return True
  except Exception as e:
    print(f"[Meeting] 写入 {persona.name} 记忆失败: {e}")
    return False


def write_round_summary_to_expert_memory(personas: Dict[str, "Persona"],
                                          round_num: int,
                                          summary: str,
                                          topic: str,
                                          created_time: datetime.datetime) -> None:
  """将每轮总结写入所有专家的长期记忆。"""
  if not summary:
    return

  for persona in personas.values():
    if not _is_expert_persona(persona):
      continue
    write_meeting_memory(persona, summary, "summary", topic, round_num, created_time)


def write_meeting_to_moderator_memory(moderator,
                                       round_speeches: List[Dict[str, str]],
                                       summary: str,
                                       topic: str,
                                       round_num: int,
                                       created_time: datetime.datetime) -> None:
  """将本轮会议内容写入主持人的记忆（包括所有专家发言和总结）。
  
  注意：专家发言会先提取要点再写入，而非写入原文。
  """
  if not moderator:
    return
  
  # 写入每个专家的发言（提取要点后）
  for speech in round_speeches:
    speaker = speech.get("speaker", "专家")
    role = speech.get("role", "expert")
    content = speech.get("content", "")
    if content:
      # 先提取要点，再写入记忆
      key_points = extract_speech_key_points(speaker, role, content, topic)
      print(f"[Memory] 为 {speaker} 的发言提取要点...")
      write_meeting_memory(
        moderator, key_points, "expert_speech", topic, round_num, created_time, speaker
      )
  
  # 写入自己的总结（总结本身已经是精炼的，直接写入）
  if summary:
    write_meeting_memory(
      moderator, summary, "summary", topic, round_num, created_time, "自己"
    )


def add_meeting_to_chat_memory(persona,
                                all_speeches: List[Dict[str, str]],
                                topic: str,
                                created_time: datetime.datetime) -> None:
  """将会议对话添加到 persona 的 seq_chat 记忆中（与原有 add_chat 一致）。
  
  这确保会议对话：
  1. 存入 seq_chat，可被 get_last_chat() 检索
  2. 减少 importance_trigger_curr，触发更频繁的反思
  """
  try:
    # 构建对话描述
    chat_description = f"参加专家会议讨论：{topic}"
    
    # 构建 chat filling（对话记录）
    chat_filling = []
    for speech in all_speeches:
      speaker = speech.get("speaker", "未知")
      content = speech.get("content", "")
      if content:
        truncated = content[:500] + "..." if len(content) > 500 else content
        chat_filling.append([speaker, truncated])
    
    if not chat_filling:
      return
    
    # 生成嵌入和重要性分数
    chat_embedding = get_embedding(chat_description)
    chat_embedding_pair = (chat_description, chat_embedding)
    
    # 专家会议对话的重要性较高
    chat_poignancy = 8  # 高重要性
    
    # 构建 SPO 三元组
    persona_name = getattr(persona.scratch, "name", persona.name)
    s = persona_name
    p = "participated in"
    o = f"专家会议-{topic[:30]}"
    
    keywords = {"专家会议", "食品安全", topic[:20], persona_name}
    
    # 调用原有的 add_chat 方法
    chat_node = persona.a_mem.add_chat(
      created_time,
      None,  # expiration
      s, p, o,
      chat_description,
      keywords,
      chat_poignancy,
      chat_embedding_pair,
      chat_filling
    )
    
    # 减少 importance_trigger_curr，触发更频繁的反思（与原有逻辑一致）
    persona.scratch.importance_trigger_curr -= chat_poignancy * 2
    persona.scratch.importance_ele_n += 1
    
    print(f"[Meeting] 已将会议对话添加到 {persona_name} 的 seq_chat 记忆")
    return chat_node
    
  except Exception as e:
    print(f"[Meeting] 添加 {persona.name} 的 chat 记忆失败: {e}")
    return None


def setup_meeting_chat_state(personas: Dict[str, "Persona"],
                              all_speeches: List[Dict[str, str]],
                              meeting_end_time: datetime.datetime,
                              topic: str) -> None:
  """为所有会议参与者设置对话状态，让原有的 reflect() 能够触发反思。
  
  这会设置：
  - persona.scratch.chat: 对话记录 [[speaker, content], ...]
  - persona.scratch.chatting_with: 对话对象（设为"专家会议"）
  - persona.scratch.chatting_end_time: 对话结束时间
  - 调用 add_chat 将对话存入 seq_chat
  """
  # 将会议发言转换为 chat 格式
  chat_records = []
  for speech in all_speeches:
    speaker = speech.get("speaker", "未知")
    content = speech.get("content", "")
    if content:
      # 截断过长的内容，避免记忆过大
      truncated = content[:1000] + "..." if len(content) > 1000 else content
      chat_records.append([speaker, truncated])
  
  if not chat_records:
    return
  
  # 为每个参与者设置对话状态
  print(f"[Meeting] 开始设置对话状态，共 {len(personas)} 个角色")
  
  for persona in personas.values():
    is_expert = _is_expert_persona(persona)
    is_moderator = _is_moderator_persona(persona)
    
    if not (is_expert or is_moderator):
      continue
    
    print(f"[Meeting] 处理角色: {persona.name} (expert={is_expert}, moderator={is_moderator})")
    
    try:
      # 1. 将会议对话添加到 seq_chat 记忆（与原有 add_chat 一致）
      add_meeting_to_chat_memory(persona, all_speeches, topic, meeting_end_time)
      
      # 2. 设置对话记录
      persona.scratch.chat = chat_records
      
      # 3. 设置对话对象为"专家会议"
      persona.scratch.chatting_with = f"专家会议-{topic[:20]}"
      
      # 4. 设置对话结束时间（让 reflect() 在下一时间步触发）
      persona.scratch.chatting_end_time = meeting_end_time
      
      print(f"[Meeting] 已为 {persona.name} 设置会议对话状态，等待反思触发")
    except Exception as e:
      import traceback
      print(f"[Meeting] 设置 {persona.name} 对话状态失败: {e}")
      traceback.print_exc()


class ExpertMeeting:
  """专家会议管理类：控制对话顺序、管理轮次、记录发言。"""

  def __init__(self, personas: Dict[str, "Persona"], topic: str, created_time: datetime.datetime):
    self.personas = personas
    self.topic = topic
    self.created_time = created_time
    self.current_round = 0
    self.all_speeches: List[Dict[str, str]] = []
    self.round_speeches: List[Dict[str, str]] = []
    self.round_summaries: List[str] = []

    # 识别主持人和专家
    self.moderator = None
    self.experts: List = []
    print(f"[Meeting] 开始识别角色，共 {len(personas)} 个 personas")
    for name, p in personas.items():
      is_mod = _is_moderator_persona(p)
      is_exp = _is_expert_persona(p)
      print(f"[Meeting] - {name}: moderator={is_mod}, expert={is_exp}")
      if is_mod:
        self.moderator = p
      elif is_exp:
        self.experts.append(p)

    print(f"[Meeting] 识别结果: 主持人={self.moderator.name if self.moderator else None}, 专家={[p.name for p in self.experts]}")
    
    # 定义专家发言顺序（可自定义）
    self.expert_order = self.experts[:]

  def get_expert_names(self) -> List[str]:
    """获取所有专家名字。"""
    return [getattr(p.scratch, "name", p.name) for p in self.experts]

  def get_expert_roles(self) -> List[str]:
    """获取所有专家角色。"""
    return [get_expert_role(p) for p in self.experts]

  def get_expert_by_name(self, name: str):
    """根据名字获取专家对象。"""
    for p in self.experts:
      if getattr(p.scratch, "name", p.name) == name:
        return p
    return None

  def update_speaking_order(self, previous_summary: str = "") -> List[str]:
    """主持人动态决定本轮发言顺序。"""
    if not self.moderator:
      return self.get_expert_names()
    
    ordered_names = moderator_decide_speaking_order(
      self.moderator,
      self.topic,
      self.get_expert_names(),
      self.get_expert_roles(),
      self.current_round + 1,  # 下一轮
      previous_summary
    )
    
    # 根据名字顺序更新 expert_order
    new_order = []
    for name in ordered_names:
      expert = self.get_expert_by_name(name)
      if expert:
        new_order.append(expert)
    
    # 补充未匹配的专家
    for p in self.experts:
      if p not in new_order:
        new_order.append(p)
    
    self.expert_order = new_order
    print(f"[Meeting] 主持人决定第 {self.current_round + 1} 轮发言顺序: {ordered_names}")
    return ordered_names

  def start_meeting(self) -> str:
    """开始会议：主持人开场（包含引导第一位专家发言）。"""
    if not self.moderator:
      return "(没有主持人)"

    # 获取第一位专家的名字
    first_expert_name = ""
    if self.expert_order:
      first_expert_name = getattr(self.expert_order[0].scratch, "name", self.expert_order[0].name)

    opening = moderator_opening_speech(
      self.moderator,
      self.topic,
      self.get_expert_names(),
      first_expert_name=first_expert_name,
      meeting_time=self.created_time  # 传入会议时间，限制记忆检索到过去24小时
    )
    self.all_speeches.append({
      "speaker": getattr(self.moderator.scratch, "name", self.moderator.name),
      "role": "moderator",
      "type": "opening",
      "content": opening
    })
    return opening

  def next_round(self) -> int:
    """开始新一轮讨论。"""
    self.current_round += 1
    self.round_speeches = []
    return self.current_round

  def get_next_expert(self) -> "Persona":
    """获取下一个应该发言的专家。"""
    idx = len(self.round_speeches) % len(self.expert_order)
    return self.expert_order[idx]

  def moderator_introduce_expert(self, next_expert) -> str:
    """主持人引导下一位专家发言。"""
    if not self.moderator:
      return ""

    next_name = getattr(next_expert.scratch, "name", next_expert.name)
    
    # 传入上一轮的总结和发言，而不是当前轮（当前轮是空的）
    previous_round_speeches = []
    if self.round_summaries:
      # 构造上一轮总结作为参考
      previous_round_speeches = [{
        "speaker": "主持人",
        "content": self.round_summaries[-1]
      }]
    
    question = moderator_question_speech(
      self.moderator,
      self.current_round,
      previous_round_speeches,
      next_name,
      self.topic
    )
    self.all_speeches.append({
      "speaker": getattr(self.moderator.scratch, "name", self.moderator.name),
      "role": "moderator",
      "type": "question",
      "content": question
    })
    return question

  def expert_speak(self, expert, question: str) -> str:
    """专家发言。"""
    global _last_expert_reasoning
    speech_func = get_expert_speech_function(expert)
    speech = speech_func(expert, question, meeting_time=self.created_time)  # 传入会议时间

    expert_name = getattr(expert.scratch, "name", expert.name)
    speech_record = {
      "speaker": expert_name,
      "role": get_expert_role(expert),
      "type": "speech",
      "content": speech,
      "reasoning": _last_expert_reasoning.copy() if _last_expert_reasoning else {}
    }
    self.all_speeches.append(speech_record)
    self.round_speeches.append(speech_record)
    return speech

  def moderator_give_feedback(self, expert, expert_speech: str) -> str:
    """主持人对专家发言给出即时反馈。"""
    if not self.moderator:
      return ""
    
    expert_name = getattr(expert.scratch, "name", expert.name)
    expert_role = get_expert_role(expert)
    
    # 获取之前的发言（不包括刚刚这条）
    previous = self.round_speeches[:-1] if len(self.round_speeches) > 1 else []
    
    feedback = moderator_feedback_to_expert(
      self.moderator,
      expert_name,
      expert_speech,
      expert_role,
      previous,
      self.topic
    )
    
    self.all_speeches.append({
      "speaker": getattr(self.moderator.scratch, "name", self.moderator.name),
      "role": "moderator",
      "type": "feedback",
      "target_expert": expert_name,
      "content": feedback
    })
    return feedback

  def moderator_give_targeted_advice(self, expert) -> str:
    """主持人在轮末对专家给出针对性意见（综合所有专家发言）。"""
    if not self.moderator:
      return ""
    
    expert_name = getattr(expert.scratch, "name", expert.name)
    expert_role = get_expert_role(expert)
    
    # 找到该专家在本轮的发言
    expert_speech = ""
    for sp in self.round_speeches:
      if sp.get("speaker") == expert_name:
        expert_speech = sp.get("content", "")
        break
    
    advice = moderator_targeted_advice(
      self.moderator,
      expert_name,
      expert_role,
      expert_speech,
      self.round_speeches,
      self.topic,
      self.current_round
    )
    
    # 记录到发言列表
    self.all_speeches.append({
      "speaker": getattr(self.moderator.scratch, "name", self.moderator.name),
      "role": "moderator",
      "type": "advice",
      "target_expert": expert_name,
      "content": advice
    })
    
    # 将意见写入该专家的记忆
    write_meeting_memory(
      expert,
      f"主持人对我的意见：{advice}",
      "moderator_advice",
      self.topic,
      self.current_round,
      self.created_time,
      "Meeting Moderator"
    )
    
    return advice

  def end_round(self, is_final_round: bool = False) -> str:
    """结束本轮讨论：主持人总结。
    
    Args:
      is_final_round: 是否是最后一轮。如果是，将生成最终总结和决策，不再提下一轮。
    """
    if not self.moderator:
      return ""

    if is_final_round:
      # 最后一轮：生成最终总结和决策
      summary = moderator_final_summary_and_decision(
        self.moderator,
        self.round_speeches,
        self.round_summaries,  # 传入前几轮的总结
        self.topic,
        meeting_time=self.created_time
      )
      summary_type = "final_summary"
    else:
      # 非最后一轮：普通总结
      summary = moderator_round_summary(
        self.moderator,
        self.current_round,
        self.round_speeches,
        self.topic,
        meeting_time=self.created_time
      )
      summary_type = "summary"
    
    self.round_summaries.append(summary)

    # 将总结写入所有专家的记忆
    write_round_summary_to_expert_memory(
      self.personas,
      self.current_round,
      summary,
      self.topic,
      self.created_time
    )
    
    # 将本轮所有专家发言和总结写入主持人的记忆
    write_meeting_to_moderator_memory(
      self.moderator,
      self.round_speeches,
      summary,
      self.topic,
      self.current_round,
      self.created_time
    )

    self.all_speeches.append({
      "speaker": getattr(self.moderator.scratch, "name", self.moderator.name),
      "role": "moderator",
      "type": summary_type,
      "content": summary,
      "reasoning": _last_expert_reasoning.copy() if _last_expert_reasoning else {}
    })
    return summary

  def get_all_speeches(self) -> List[Dict[str, str]]:
    """获取所有发言记录。"""
    return self.all_speeches

  def finalize_meeting(self) -> None:
    """会议结束时调用：设置对话状态，让原有的 reflect() 触发反思。
    
    这会为所有参与者设置 chat、chatting_with、chatting_end_time，
    使得在下一个时间步时，原有的反思机制会自动生成：
    - planning_thought: 规划相关反思
    - memo_thought: 对话备忘反思
    
    同时，将最终决策写入所有平民的记忆。
    """
    # 计算会议结束时间（当前时间 + 几秒）
    meeting_end_time = self.created_time + datetime.timedelta(seconds=5)
    
    setup_meeting_chat_state(
      self.personas,
      self.all_speeches,
      meeting_end_time,
      self.topic
    )
    print(f"[Meeting] 会议已结束，反思将在下一时间步触发")
    
    # 将最终决策写入平民记忆
    if self.round_summaries:
      final_decision = self.round_summaries[-1]  # 最后一轮的总结就是最终决策
      
      # 提取平民版决策
      print(f"[Meeting] 正在提取平民版决策...")
      civilian_decision = extract_decision_for_civilians(final_decision, self.topic)
      
      if civilian_decision:
        # 写入所有平民的记忆
        broadcast_decision_to_civilians(
          self.personas,
          civilian_decision,
          self.topic,
          meeting_end_time
        )
        print(f"[Meeting] 平民版决策已广播完成")

  def run_full_round(self, use_dynamic_order: bool = True) -> List[Dict[str, str]]:
    """运行完整的一轮讨论：
    
    新流程：
    1. 主持人决定顺序
    2. 主持人简短引导
    3. 专家A发言 → 专家B发言 → 专家C发言（连续发言）
    4. 主持人总结（写入所有专家记忆）
    5. 主持人对专家A意见 → 对专家B意见 → 对专家C意见
    
    Args:
      use_dynamic_order: 是否让主持人动态决定发言顺序
    """
    round_results = []
    
    # 主持人动态决定本轮发言顺序
    if use_dynamic_order and self.moderator:
      previous_summary = self.round_summaries[-1] if self.round_summaries else ""
      ordered_names = self.update_speaking_order(previous_summary)
      round_results.append({
        "type": "speaking_order",
        "order": ordered_names
      })
    
    self.next_round()

    # 阶段1：主持人引导（第一轮跳过，因为开场白已包含引导）
    question = ""
    if self.current_round > 1:
      first_expert = self.expert_order[0]
      question = self.moderator_introduce_expert(first_expert)
      round_results.append({
        "type": "moderator_question",
        "content": question
      })
    else:
      # 第一轮：使用会议主题作为问题
      question = self.topic

    # 阶段2：所有专家依次发言（不插入反馈）
    for expert in self.expert_order:
      speech = self.expert_speak(expert, question)
      expert_name = getattr(expert.scratch, "name", expert.name)
      round_results.append({
        "type": "expert_speech",
        "speaker": expert_name,
        "content": speech
      })
      print(f"[Meeting] {expert_name} 发言完成")

    # 阶段3：主持人总结（写入所有专家记忆）
    summary = self.end_round()
    round_results.append({
      "type": "round_summary",
      "content": summary
    })
    print(f"[Meeting] 主持人总结完成")

    # 阶段4：主持人对每个专家给出针对性意见
    for expert in self.expert_order:
      expert_name = getattr(expert.scratch, "name", expert.name)
      advice = self.moderator_give_targeted_advice(expert)
      round_results.append({
        "type": "advice",
        "target_expert": expert_name,
        "content": advice
      })
      print(f"[Meeting] 主持人对 {expert_name} 的意见完成")

    return round_results

  def run_full_round_streaming(self, on_speech_callback, use_dynamic_order: bool = True, is_final_round: bool = False) -> List[Dict[str, str]]:
    """运行完整的一轮讨论（流式版本，每生成一条发言就回调更新）。
    
    Args:
      on_speech_callback: 回调函数
      use_dynamic_order: 是否让主持人动态决定发言顺序
      is_final_round: 是否是最后一轮。如果是，将生成最终总结和决策，不再对专家提意见。
    
    流程：
    1. 主持人决定顺序
    2. 主持人简短引导（第2轮+）
    3. 专家A发言 → 专家B发言 → 专家C发言
    4. 主持人总结+对各专家意见（合并为一段话）
    
    Args:
      on_speech_callback: 回调函数 (speeches, status, pending_speaker) -> None
      use_dynamic_order: 是否让主持人动态决定发言顺序
    """
    round_results = []
    
    # 主持人动态决定本轮发言顺序
    if use_dynamic_order and self.moderator:
      previous_summary = self.round_summaries[-1] if self.round_summaries else ""
      ordered_names = self.update_speaking_order(previous_summary)
      round_results.append({
        "type": "speaking_order",
        "order": ordered_names
      })
    
    self.next_round()

    # 阶段1：主持人引导（第一轮跳过，因为开场白已包含引导）
    question = ""
    if self.current_round > 1:
      first_expert = self.expert_order[0]
      on_speech_callback(self.get_all_speeches(), "in_progress", "主持人引导中...")
      question = self.moderator_introduce_expert(first_expert)
      round_results.append({
        "type": "moderator_question",
        "content": question
      })
      on_speech_callback(self.get_all_speeches(), "in_progress", None)
    else:
      # 第一轮：从开场白中提取问题（或使用默认问题）
      question = self.topic

    # 阶段2：所有专家依次发言（不插入反馈）
    for expert in self.expert_order:
      expert_name = getattr(expert.scratch, "name", expert.name)
      
      on_speech_callback(self.get_all_speeches(), "in_progress", f"{expert_name} 发言中...")
      speech = self.expert_speak(expert, question)
      round_results.append({
        "type": "expert_speech",
        "speaker": expert_name,
        "content": speech
      })
      on_speech_callback(self.get_all_speeches(), "in_progress", None)
      print(f"[Meeting] {expert_name} 发言完成")

    # 阶段3：主持人总结
    if is_final_round:
      on_speech_callback(self.get_all_speeches(), "in_progress", "主持人生成最终总结与决策...")
      summary = self.end_round(is_final_round=True)
      round_results.append({
        "type": "final_summary",
        "content": summary
      })
      on_speech_callback(self.get_all_speeches(), "in_progress", None)
      print(f"[Meeting] 最终总结与决策完成")
      # 最后一轮不再对专家提意见
    else:
      on_speech_callback(self.get_all_speeches(), "in_progress", "主持人总结中...")
      summary = self.end_round(is_final_round=False)
      round_results.append({
        "type": "round_summary",
        "content": summary
      })
      on_speech_callback(self.get_all_speeches(), "in_progress", None)
      print(f"[Meeting] 主持人总结完成")

      # 阶段4：主持人对每个专家给出针对性意见（仅非最后一轮）
      for expert in self.expert_order:
        expert_name = getattr(expert.scratch, "name", expert.name)
        
        on_speech_callback(self.get_all_speeches(), "in_progress", f"对 {expert_name} 提出意见...")
        advice = self.moderator_give_targeted_advice(expert)
        round_results.append({
          "type": "advice",
          "target_expert": expert_name,
          "content": advice
        })
        on_speech_callback(self.get_all_speeches(), "in_progress", None)
        print(f"[Meeting] 主持人对 {expert_name} 的意见完成")

    return round_results
