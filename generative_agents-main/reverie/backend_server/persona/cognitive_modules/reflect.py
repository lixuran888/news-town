"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reflect.py
Description: This defines the "Reflect" module for generative agents. 
"""
import sys
sys.path.append('../../')

import datetime
import random

from numpy import dot
from numpy.linalg import norm

from global_methods import *
from persona.prompt_template.run_gpt_prompt import *
from persona.prompt_template.gpt_structure import *
from persona.cognitive_modules.retrieve import *

def process_memo_thought(persona, other_name, memo_thought):
  """
  处理 memo_thought，一次性提取：
  1. 关系变化 → 更新 friends
  2. 事件舆论 → 存入 event_opinions
  
  memo_thought 格式: 
  "{memo} | relationship: {xxx} | event_opinion: {xxx} | stance: {xxx}"
  """
  if not other_name or not memo_thought:
    return
  
  memo_lower = memo_thought.lower()
  
  # ===== 1. 解析关系标签并更新 friends =====
  relationship = "unchanged"
  if "| relationship:" in memo_lower:
    try:
      # 提取 relationship 部分
      rel_part = memo_lower.split("| relationship:")[1]
      relationship = rel_part.split("|")[0].strip()
      relationship = relationship.replace('"', '').replace("'", "").strip()
    except:
      relationship = "unchanged"
  
  friends = persona.scratch.friends
  all_known = (friends.get("best_friends", []) + 
               friends.get("good_friends", []) + 
               friends.get("acquaintances", []) + 
               friends.get("tensions", []))
  is_new_person = other_name not in all_known
  
  # 新认识的人
  if is_new_person or "new_acquaintance" in relationship:
    if other_name not in friends.get("acquaintances", []):
      if "acquaintances" not in friends:
        friends["acquaintances"] = []
      friends["acquaintances"].append(other_name)
      print(f"[Friends] {persona.scratch.name} 新认识了 {other_name}")
  
  # 关系恶化
  elif "worsened" in relationship:
    if other_name not in friends.get("tensions", []):
      if "tensions" not in friends:
        friends["tensions"] = []
      friends["tensions"].append(other_name)
      print(f"[Friends] {persona.scratch.name} 与 {other_name} 关系恶化")
  
  # 关系改善
  elif "improved" in relationship:
    if other_name in friends.get("acquaintances", []):
      friends["acquaintances"].remove(other_name)
      if "good_friends" not in friends:
        friends["good_friends"] = []
      if other_name not in friends["good_friends"]:
        friends["good_friends"].append(other_name)
        print(f"[Friends] {persona.scratch.name} 与 {other_name} 升级为 good_friends")
    if other_name in friends.get("tensions", []):
      friends["tensions"].remove(other_name)
      print(f"[Friends] {persona.scratch.name} 与 {other_name} 和解")

  # ===== 2. 解析事件舆论并存入 event_opinions =====
  event_opinion = None
  stance = "none"
  
  if "| event_opinion:" in memo_lower:
    try:
      # 提取 event_opinion 部分
      opinion_part = memo_lower.split("| event_opinion:")[1]
      event_opinion = opinion_part.split("| stance:")[0].strip()
      event_opinion = event_opinion.replace('"', '').replace("'", "").strip()
      
      # 提取 stance
      if "| stance:" in memo_lower:
        stance_part = memo_lower.split("| stance:")[1]
        stance = stance_part.split("|")[0].strip()
        stance = stance.replace('"', '').replace("'", "").strip()
    except:
      pass
  
  # 如果有有效的事件舆论，存入 event_opinions
  if event_opinion and event_opinion != "none" and len(event_opinion) > 5:
    if not hasattr(persona.scratch, 'event_opinions'):
      persona.scratch.event_opinions = []
    
    # 避免重复
    existing = [o.get("opinion", "")[:30] for o in persona.scratch.event_opinions]
    if event_opinion[:30] not in existing:
      opinion_data = {
        "speaker": persona.scratch.name,
        "other": other_name,
        "opinion": event_opinion,
        "stance": stance if stance != "none" else "neutral",
        "time": persona.scratch.curr_time.strftime("%H:%M") if persona.scratch.curr_time else "unknown"
      }
      persona.scratch.event_opinions.append(opinion_data)
      print(f"[EventOpinion] {persona.scratch.name}: {stance} - {event_opinion[:50]}...")


def generate_focal_points(persona, n=3): 
  if debug: print ("GNS FUNCTION: <generate_focal_points>")
  
  nodes = [[i.last_accessed, i]
            for i in persona.a_mem.seq_event + persona.a_mem.seq_thought
            if "idle" not in i.embedding_key]

  nodes = sorted(nodes, key=lambda x: x[0])
  nodes = [i for created, i in nodes]

  statements = ""
  for node in nodes[-1*persona.scratch.importance_ele_n:]: 
    statements += node.embedding_key + "\n"

  return run_gpt_prompt_focal_pt(persona, statements, n)[0]


def generate_insights_and_evidence(persona, nodes, n=5): 
  if debug: print ("GNS FUNCTION: <generate_insights_and_evidence>")

  statements = ""
  for count, node in enumerate(nodes): 
    statements += f'{str(count)}. {node.embedding_key}\n'

  ret = run_gpt_prompt_insight_and_guidance(persona, statements, n)[0]

  print(ret)
  
  if not ret or not isinstance(ret, dict):
    print(f"[Warning] LLM 返回无效: {ret}")
    return {}
  
  try: 
    valid_ret = {}
    for thought, evi_raw in ret.items(): 
      # 过滤越界索引
      valid_indices = [i for i in evi_raw if 0 <= i < len(nodes)]
      if valid_indices:
        evidence_node_id = [nodes[i].node_id for i in valid_indices]
        valid_ret[thought] = evidence_node_id
      else:
        print(f"[Warning] 反思 '{thought[:30]}...' 的证据索引无效: {evi_raw}")
    return valid_ret
  except Exception as e: 
    print(f"[Warning] generate_insights_and_evidence 解析失败: {e}")
    return {} 


def generate_action_event_triple(act_desp, persona): 
  """TODO 

  INPUT: 
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT: 
    a string of emoji that translates action description.
  EXAMPLE OUTPUT: 
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_event_triple>")
  return run_gpt_prompt_event_triple(act_desp, persona)[0]


def generate_poig_score(persona, event_type, description): 
  if debug: print ("GNS FUNCTION: <generate_poig_score>")

  if "is idle" in description: 
    return 1

  if event_type == "event" or event_type == "thought": 
    return run_gpt_prompt_event_poignancy(persona, description)[0]
  elif event_type == "chat": 
    return run_gpt_prompt_chat_poignancy(persona, 
                           persona.scratch.act_description)[0]



def generate_planning_thought_on_convo(persona, all_utt):
  if debug: print ("GNS FUNCTION: <generate_planning_thought_on_convo>")
  return run_gpt_prompt_planning_thought_on_convo(persona, all_utt)[0]


def generate_memo_on_convo(persona, all_utt):
  if debug: print ("GNS FUNCTION: <generate_memo_on_convo>")
  return run_gpt_prompt_memo_on_convo(persona, all_utt)[0]




def run_reflect(persona):
  """
  Run the actual reflection. We generate the focal points, retrieve any 
  relevant nodes, and generate thoughts and insights. 

  INPUT: 
    persona: Current Persona object
  Output: 
    None
  """
  # Reflection requires certain focal points. Generate that first. 
  focal_points = generate_focal_points(persona, 3)
  # Retrieve the relevant Nodes object for each of the focal points. 
  # <retrieved> has keys of focal points, and values of the associated Nodes. 
  retrieved = new_retrieve(persona, focal_points)

  # For each of the focal points, generate thoughts and save it in the 
  # agent's memory. 
  for focal_pt, nodes in retrieved.items(): 
    xx = [i.embedding_key for i in nodes]
    for xxx in xx: print (xxx)

    thoughts = generate_insights_and_evidence(persona, nodes, 5)
    for thought, evidence in thoughts.items(): 
      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      s, p, o = generate_action_event_triple(thought, persona)
      keywords = set([s, p, o])
      thought_poignancy = generate_poig_score(persona, "thought", thought)
      thought_embedding_pair = (thought, get_embedding(thought))

      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)


def reflection_trigger(persona): 
  """
  Given the current persona, determine whether the persona should run a 
  reflection. 
  
  Our current implementation checks for whether the sum of the new importance
  measure has reached the set (hyper-parameter) threshold.

  INPUT: 
    persona: Current Persona object
  Output: 
    True if we are running a new reflection. 
    False otherwise. 
  """
  print (persona.scratch.name, "persona.scratch.importance_trigger_curr::", persona.scratch.importance_trigger_curr)
  print (persona.scratch.importance_trigger_max)

  if (persona.scratch.importance_trigger_curr <= 0 and 
      [] != persona.a_mem.seq_event + persona.a_mem.seq_thought): 
    return True 
  return False


def reset_reflection_counter(persona): 
  """
  We reset the counters used for the reflection trigger. 

  INPUT: 
    persona: Current Persona object
  Output: 
    None
  """
  persona_imt_max = persona.scratch.importance_trigger_max
  persona.scratch.importance_trigger_curr = persona_imt_max
  persona.scratch.importance_ele_n = 0


def reflect(persona):
  """
  The main reflection module for the persona. We first check if the trigger 
  conditions are met, and if so, run the reflection and reset any of the 
  relevant counters. 

  INPUT: 
    persona: Current Persona object
  Output: 
    None
  """
  if reflection_trigger(persona): 
    run_reflect(persona)
    reset_reflection_counter(persona)



  # print (persona.scratch.name, "al;sdhfjlsad", persona.scratch.chatting_end_time)
  if persona.scratch.chatting_end_time: 
    # print("DEBUG", persona.scratch.curr_time + datetime.timedelta(0,10))
    if persona.scratch.curr_time + datetime.timedelta(0,10) >= persona.scratch.chatting_end_time: 
      # print ("KABOOOOOMMMMMMM")
      all_utt = ""
      if persona.scratch.chat: 
        for row in persona.scratch.chat:  
          all_utt += f"{row[0]}: {row[1]}\n"

      # planning_thought = generate_planning_thought_on_convo(persona, all_utt)
      # print ("init planning: aosdhfpaoisdh90m     ::", f"For {persona.scratch.name}'s planning: {planning_thought}")
      # planning_thought = generate_planning_thought_on_convo(target_persona, all_utt)
      # print ("target planning: aosdhfpaodish90m     ::", f"For {target_persona.scratch.name}'s planning: {planning_thought}")

      # memo_thought = generate_memo_on_convo(persona, all_utt)
      # print ("init memo: aosdhfpaoisdh90m     ::", f"For {persona.scratch.name} {memo_thought}")
      # memo_thought = generate_memo_on_convo(target_persona, all_utt)
      # print ("target memo: aosdhfpsaoish90m     ::", f"For {target_persona.scratch.name} {memo_thought}")
      

      # make sure you set the fillings as well

      # print (persona.a_mem.get_last_chat(persona.scratch.chatting_with).node_id)

      evidence = [persona.a_mem.get_last_chat(persona.scratch.chatting_with).node_id]

      planning_thought = generate_planning_thought_on_convo(persona, all_utt)
      planning_thought = f"For {persona.scratch.name}'s planning: {planning_thought}"

      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      s, p, o = generate_action_event_triple(planning_thought, persona)
      keywords = set([s, p, o])
      thought_poignancy = generate_poig_score(persona, "thought", planning_thought)
      thought_embedding_pair = (planning_thought, get_embedding(planning_thought))

      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                planning_thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)



      memo_thought = generate_memo_on_convo(persona, all_utt)
      memo_thought = f"{persona.scratch.name} {memo_thought}"

      created = persona.scratch.curr_time
      expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
      s, p, o = generate_action_event_triple(memo_thought, persona)
      keywords = set([s, p, o])
      thought_poignancy = generate_poig_score(persona, "thought", memo_thought)
      thought_embedding_pair = (memo_thought, get_embedding(memo_thought))

      persona.a_mem.add_thought(created, expiration, s, p, o, 
                                memo_thought, keywords, thought_poignancy, 
                                thought_embedding_pair, evidence)

      # 一次性处理：更新朋友关系 + 提取事件舆论
      process_memo_thought(persona, 
                           persona.scratch.chatting_with, 
                           memo_thought)

      # 清空对话状态，标记对话已结束
      print(f"[Chat End] {persona.scratch.name} 与 {persona.scratch.chatting_with} 的对话结束")
      persona.scratch.chatting_with = None
      persona.scratch.chat = None
      persona.scratch.chatting_end_time = None





















