import datetime
from typing import Set

from persona.prompt_template.gpt_structure import get_embedding


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
