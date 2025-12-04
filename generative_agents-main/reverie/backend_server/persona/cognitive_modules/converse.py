"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: converse.py
Description: An extra cognitive module for generating conversations. 
"""
import math
import sys
import datetime
import random
sys.path.append('../')

from global_methods import *

# 情感分析模块
try:
    from sentiment.sentiment_analysis import analyze_sentiment, get_sentiment_summary
    SENTIMENT_ENABLED = True
    print("[Converse] 情感分析模块已加载")
except ImportError:
    SENTIMENT_ENABLED = False
    print("[Converse] 情感分析模块未加载，将跳过情感标签")

from persona.memory_structures.spatial_memory import *
from persona.memory_structures.associative_memory import *
from persona.memory_structures.scratch import *
from persona.cognitive_modules.retrieve import *
from persona.prompt_template.run_gpt_prompt import *

def generate_agent_chat_summarize_ideas(init_persona, 
                                        target_persona, 
                                        retrieved, 
                                        curr_context): 
  all_embedding_keys = list()
  for key, val in retrieved.items(): 
    for i in val: 
      all_embedding_keys += [i.embedding_key]
  all_embedding_key_str =""
  for i in all_embedding_keys: 
    all_embedding_key_str += f"{i}\n"

  try: 
    summarized_idea = run_gpt_prompt_agent_chat_summarize_ideas(init_persona,
                        target_persona, all_embedding_key_str, 
                        curr_context)[0]
  except:
    summarized_idea = ""
  return summarized_idea


def generate_summarize_agent_relationship(init_persona, 
                                          target_persona, 
                                          retrieved): 
  all_embedding_keys = list()
  for key, val in retrieved.items(): 
    for i in val: 
      all_embedding_keys += [i.embedding_key]
  all_embedding_key_str =""
  for i in all_embedding_keys: 
    all_embedding_key_str += f"{i}\n"

  summarized_relationship = run_gpt_prompt_agent_chat_summarize_relationship(
                              init_persona, target_persona,
                              all_embedding_key_str)[0]
  return summarized_relationship


def generate_agent_chat(maze, 
                        init_persona, 
                        target_persona,
                        curr_context, 
                        init_summ_idea, 
                        target_summ_idea): 
  summarized_idea = run_gpt_prompt_agent_chat(maze, 
                                              init_persona, 
                                              target_persona,
                                              curr_context, 
                                              init_summ_idea, 
                                              target_summ_idea)[0]
  for i in summarized_idea: 
    print (i)
  return summarized_idea


def agent_chat_v1(maze, init_persona, target_persona): 
  # Chat version optimized for speed via batch generation
  curr_context = (f"{init_persona.scratch.name} " + 
              f"was {init_persona.scratch.act_description} " + 
              f"when {init_persona.scratch.name} " + 
              f"saw {target_persona.scratch.name} " + 
              f"in the middle of {target_persona.scratch.act_description}.\n")
  curr_context += (f"{init_persona.scratch.name} " +
              f"is thinking of initating a conversation with " +
              f"{target_persona.scratch.name}.")

  summarized_ideas = []
  part_pairs = [(init_persona, target_persona), 
                (target_persona, init_persona)]
  for p_1, p_2 in part_pairs: 
    focal_points = [f"{p_2.scratch.name}"]
    retrieved = new_retrieve(p_1, focal_points, 50)
    relationship = generate_summarize_agent_relationship(p_1, p_2, retrieved)
    focal_points = [f"{relationship}", 
                    f"{p_2.scratch.name} is {p_2.scratch.act_description}"]
    retrieved = new_retrieve(p_1, focal_points, 25)
    summarized_idea = generate_agent_chat_summarize_ideas(p_1, p_2, retrieved, curr_context)
    summarized_ideas += [summarized_idea]

  return generate_agent_chat(maze, init_persona, target_persona, 
                      curr_context, 
                      summarized_ideas[0], 
                      summarized_ideas[1])


def generate_one_utterance(maze, init_persona, target_persona, retrieved, curr_chat): 
  # Chat version optimized for speed via batch generation
  curr_context = (f"{init_persona.scratch.name} " + 
              f"was {init_persona.scratch.act_description} " + 
              f"when {init_persona.scratch.name} " + 
              f"saw {target_persona.scratch.name} " + 
              f"in the middle of {target_persona.scratch.act_description}.\n")
  curr_context += (f"{init_persona.scratch.name} " +
              f"is initiating a conversation with " +
              f"{target_persona.scratch.name}.")

  x = run_gpt_generate_iterative_chat_utt(maze, init_persona, target_persona, retrieved, curr_context, curr_chat)[0]

  return x["utterance"], x["end"]

def agent_chat_v2(maze, init_persona, target_persona): 
  curr_chat = []  # [[speaker, utterance], ...]
  curr_chat_with_sentiment = []  # [[speaker, utterance, sentiment_info], ...]

  for i in range(8): 
    focal_points = [f"{target_persona.scratch.name}"]
    retrieved = new_retrieve(init_persona, focal_points, 50)
    relationship = generate_summarize_agent_relationship(init_persona, target_persona, retrieved)
    last_chat = ""
    for i in curr_chat[-4:]:
      last_chat += ": ".join(i) + "\n"
    if last_chat: 
      focal_points = [f"{relationship}", 
                      f"{target_persona.scratch.name} is {target_persona.scratch.act_description}", 
                      last_chat]
    else: 
      focal_points = [f"{relationship}", 
                      f"{target_persona.scratch.name} is {target_persona.scratch.act_description}"]
    retrieved = new_retrieve(init_persona, focal_points, 15)
    utt, end = generate_one_utterance(maze, init_persona, target_persona, retrieved, curr_chat)

    # 情感分析
    if SENTIMENT_ENABLED:
      sentiment = analyze_sentiment(utt)
      emoji = "😊" if sentiment["label"] == "positive" else ("😟" if sentiment["label"] == "negative" else "😐")
      print(f"[Sentiment] {init_persona.scratch.name}: {utt[:50]}... [{emoji} {sentiment['label']} {sentiment['score']:+.2f}]")
      curr_chat_with_sentiment.append([init_persona.scratch.name, utt, sentiment])
    else:
      curr_chat_with_sentiment.append([init_persona.scratch.name, utt, None])

    curr_chat += [[init_persona.scratch.name, utt]]
    if end:
      break


    focal_points = [f"{init_persona.scratch.name}"]
    retrieved = new_retrieve(target_persona, focal_points, 50)
    relationship = generate_summarize_agent_relationship(target_persona, init_persona, retrieved)
    print ("-------- relationshopadsjfhkalsdjf", relationship)
    last_chat = ""
    for i in curr_chat[-4:]:
      last_chat += ": ".join(i) + "\n"
    if last_chat: 
      focal_points = [f"{relationship}", 
                      f"{init_persona.scratch.name} is {init_persona.scratch.act_description}", 
                      last_chat]
    else: 
      focal_points = [f"{relationship}", 
                      f"{init_persona.scratch.name} is {init_persona.scratch.act_description}"]
    retrieved = new_retrieve(target_persona, focal_points, 15)
    utt, end = generate_one_utterance(maze, target_persona, init_persona, retrieved, curr_chat)

    # 情感分析
    if SENTIMENT_ENABLED:
      sentiment = analyze_sentiment(utt)
      emoji = "😊" if sentiment["label"] == "positive" else ("😟" if sentiment["label"] == "negative" else "😐")
      print(f"[Sentiment] {target_persona.scratch.name}: {utt[:50]}... [{emoji} {sentiment['label']} {sentiment['score']:+.2f}]")
      curr_chat_with_sentiment.append([target_persona.scratch.name, utt, sentiment])
    else:
      curr_chat_with_sentiment.append([target_persona.scratch.name, utt, None])

    curr_chat += [[target_persona.scratch.name, utt]]
    if end:
      break

  # 输出对话和情感汇总
  print ("=" * 60)
  print ("[对话记录 with 情感标签]")
  for row in curr_chat_with_sentiment: 
    if row[2]:  # 有情感信息
      emoji = "😊" if row[2]["label"] == "positive" else ("😟" if row[2]["label"] == "negative" else "😐")
      print(f"  {row[0]}: {row[1]} [{emoji} {row[2]['label']} {row[2]['score']:+.2f}]")
    else:
      print(f"  {row[0]}: {row[1]}")
  
  # 情感汇总
  if SENTIMENT_ENABLED:
    summary = get_sentiment_summary(curr_chat)
    print ("=" * 60)
    print ("[情感汇总]")
    print (f"  总对话数: {summary['total_utterances']}")
    print (f"  正面: {summary['positive_count']} | 负面: {summary['negative_count']} | 中性: {summary['neutral_count']}")
    print (f"  平均情感分: {summary['average_score']:+.3f}")
    print (f"  情感趋势: {summary['sentiment_trend']}")
  print ("=" * 60)

  # 返回对话，直接在文本中加入情感标签
  # 格式: [[speaker, "utterance [😊positive]"], ...]
  chat_with_emoji = []
  for row in curr_chat_with_sentiment:
    speaker = row[0]
    utterance = row[1]
    sentiment = row[2]
    if sentiment:
      emoji = "😊" if sentiment["label"] == "positive" else ("😟" if sentiment["label"] == "negative" else "😐")
      # 在文本末尾加上情感标签
      utterance_with_tag = f"{utterance} [{emoji}{sentiment['label']}]"
    else:
      utterance_with_tag = utterance
    chat_with_emoji.append([speaker, utterance_with_tag])
  
  return chat_with_emoji






def generate_summarize_ideas(persona, nodes, question): 
  statements = ""
  for n in nodes:
    statements += f"{n.embedding_key}\n"
  summarized_idea = run_gpt_prompt_summarize_ideas(persona, statements, question)[0]
  return summarized_idea


def generate_next_line(persona, interlocutor_desc, curr_convo, summarized_idea):
  # Original chat -- line by line generation 
  prev_convo = ""
  for row in curr_convo: 
    prev_convo += f'{row[0]}: {row[1]}\n'

  next_line = run_gpt_prompt_generate_next_convo_line(persona, 
                                                      interlocutor_desc, 
                                                      prev_convo, 
                                                      summarized_idea)[0]  
  return next_line


def generate_inner_thought(persona, whisper):
  inner_thought = run_gpt_prompt_generate_whisper_inner_thought(persona, whisper)[0]
  return inner_thought

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


def load_history_via_whisper(personas, whispers):
  for count, row in enumerate(whispers): 
    persona = personas[row[0]]
    whisper = row[1]

    thought = generate_inner_thought(persona, whisper)

    created = persona.scratch.curr_time
    expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
    s, p, o = generate_action_event_triple(thought, persona)
    keywords = set([s, p, o])
    thought_poignancy = generate_poig_score(persona, "event", whisper)
    thought_embedding_pair = (thought, get_embedding(thought))
    persona.a_mem.add_thought(created, expiration, s, p, o, 
                              thought, keywords, thought_poignancy, 
                              thought_embedding_pair, None)


def open_convo_session(persona, convo_mode): 
  if convo_mode == "analysis": 
    curr_convo = []
    interlocutor_desc = "Interviewer"

    while True: 
      line = input("Enter Input: ")
      if line == "end_convo": 
        break

      if int(run_gpt_generate_safety_score(persona, line)[0]) >= 8: 
        print (f"{persona.scratch.name} is a computational agent, and as such, it may be inappropriate to attribute human agency to the agent in your communication.")        

      else: 
        retrieved = new_retrieve(persona, [line], 50)[line]
        summarized_idea = generate_summarize_ideas(persona, retrieved, line)
        curr_convo += [[interlocutor_desc, line]]

        next_line = generate_next_line(persona, interlocutor_desc, curr_convo, summarized_idea)
        curr_convo += [[persona.scratch.name, next_line]]


  elif convo_mode == "whisper": 
    whisper = input("Enter Input: ")
    thought = generate_inner_thought(persona, whisper)

    created = persona.scratch.curr_time
    expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
    s, p, o = generate_action_event_triple(thought, persona)
    keywords = set([s, p, o])
    thought_poignancy = generate_poig_score(persona, "event", whisper)
    thought_embedding_pair = (thought, get_embedding(thought))
    persona.a_mem.add_thought(created, expiration, s, p, o, 
                              thought, keywords, thought_poignancy, 
                              thought_embedding_pair, None)
































