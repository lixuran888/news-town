"""
Author: Joon Sung Park (joonspk@stanford.edu)
File: views.py
"""
import os
import string
import random
import json
from os import listdir
import os

import datetime
import sys
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

# 添加 global_methods 的路径
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'generative_agents-main', 'reverie', 'backend_server'))
from global_methods import *

from django.contrib.staticfiles.templatetags.staticfiles import static
from .models import *
from pathlib import Path

# 情感分析模块
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'generative_agents-main', 'reverie', 'backend_server'))
    from sentiment.sentiment_analysis import analyze_sentiment, get_sentiment_summary
    SENTIMENT_ENABLED = True
except ImportError:
    SENTIMENT_ENABLED = False

def landing(request): 
  context = {}
  template = "landing/landing.html"
  return render(request, template, context)


def demo(request, sim_code, step, play_speed="2"): 
  move_file = f"compressed_storage/{sim_code}/master_movement.json"
  meta_file = f"compressed_storage/{sim_code}/meta.json"
  step = int(step)
  play_speed_opt = {"1": 1, "2": 2, "3": 4,
                    "4": 8, "5": 16, "6": 32}
  if play_speed not in play_speed_opt: play_speed = 2
  else: play_speed = play_speed_opt[play_speed]

  # Loading the basic meta information about the simulation.
  meta = dict() 
  with open (meta_file) as json_file: 
    meta = json.load(json_file)

  sec_per_step = meta["sec_per_step"]
  start_datetime = datetime.datetime.strptime(meta["start_date"] + " 00:00:00", 
                                              '%B %d, %Y %H:%M:%S')
  for i in range(step): 
    start_datetime += datetime.timedelta(seconds=sec_per_step)
  start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

  # Loading the movement file
  raw_all_movement = dict()
  with open(move_file) as json_file: 
    raw_all_movement = json.load(json_file)
 
  # Loading all names of the personas
  persona_names = dict()
  persona_names = []
  persona_names_set = set()
  for p in list(raw_all_movement["0"].keys()): 
    persona_names += [{"original": p, 
                       "underscore": p.replace(" ", "_"), 
                       "initial": p[0] + p.split(" ")[-1][0]}]
    persona_names_set.add(p)

  # <all_movement> is the main movement variable that we are passing to the 
  # frontend. Whereas we use ajax scheme to communicate steps to the frontend
  # during the simulation stage, for this demo, we send all movement 
  # information in one step. 
  all_movement = dict()

  # Preparing the initial step. 
  # <init_prep> sets the locations and descriptions of all agents at the
  # beginning of the demo determined by <step>. 
  init_prep = dict() 
  for int_key in range(step+1): 
    key = str(int_key)
    val = raw_all_movement[key]
    for p in persona_names_set: 
      if p in val: 
        init_prep[p] = val[p]
  persona_init_pos = dict()
  for p in persona_names_set: 
    persona_init_pos[p.replace(" ","_")] = init_prep[p]["movement"]
  all_movement[step] = init_prep

  # Finish loading <all_movement>
  for int_key in range(step+1, len(raw_all_movement.keys())): 
    all_movement[int_key] = raw_all_movement[str(int_key)]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": json.dumps(persona_init_pos), 
             "all_movement": json.dumps(all_movement), 
             "start_datetime": start_datetime,
             "sec_per_step": sec_per_step,
             "play_speed": play_speed,
             "mode": "demo"}
  template = "demo/demo.html"

  return render(request, template, context)


def UIST_Demo(request): 
  return demo(request, "March20_the_ville_n25_UIST_RUN-step-1-141", 2160, play_speed="3")


def home(request):
  f_curr_sim_code = "temp_storage/curr_sim_code.json"
  f_curr_step = "temp_storage/curr_step.json"

  if not check_if_file_exists(f_curr_step): 
    context = {}
    template = "home/error_start_backend.html"
    return render(request, template, context)

  with open(f_curr_sim_code) as json_file:  
    sim_code = json.load(json_file)["sim_code"]
  
  with open(f_curr_step) as json_file:  
    step = json.load(json_file)["step"]

  os.remove(f_curr_step)

  persona_names = []
  persona_names_set = set()
  for i in find_filenames(f"storage/{sim_code}/personas", ""): 
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      persona_names += [[x, x.replace(" ", "_")]]
      persona_names_set.add(x)

  persona_init_pos = []
  file_count = []
  for i in find_filenames(f"storage/{sim_code}/environment", ".json"):
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      file_count += [int(x.split(".")[0])]
  curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
  with open(curr_json) as json_file:  
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items(): 
      if key in persona_names_set: 
        persona_init_pos += [[key, val["x"], val["y"]]]

  context = {"sim_code": sim_code,
             "step": step, 
             "persona_names": persona_names,
             "persona_init_pos": persona_init_pos,
             "mode": "simulate"}
  template = "home/home.html"
  return render(request, template, context)


def replay(request, sim_code, step): 
  sim_code = sim_code
  step = int(step)

  persona_names = []
  persona_names_set = set()
  for i in find_filenames(f"storage/{sim_code}/personas", ""): 
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      persona_names += [[x, x.replace(" ", "_")]]
      persona_names_set.add(x)

  persona_init_pos = []
  file_count = []
  for i in find_filenames(f"storage/{sim_code}/environment", ".json"):
    x = i.split("/")[-1].strip()
    if x[0] != ".": 
      file_count += [int(x.split(".")[0])]
  curr_json = f'storage/{sim_code}/environment/{str(max(file_count))}.json'
  with open(curr_json) as json_file:  
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items(): 
      if key in persona_names_set: 
        persona_init_pos += [[key, val["x"], val["y"]]]

  context = {"sim_code": sim_code,
             "step": step,
             "persona_names": persona_names,
             "persona_init_pos": persona_init_pos, 
             "mode": "replay"}
  template = "home/home.html"
  return render(request, template, context)


def replay_persona_state(request, sim_code, step, persona_name): 
  sim_code = sim_code
  step = int(step)

  persona_name_underscore = persona_name
  persona_name = " ".join(persona_name.split("_"))
  
  # Try multiple possible locations for persona data
  memory = None
  possible_paths = [
    f"storage/{sim_code}/personas/{persona_name}/bootstrap_memory",
    f"storage/{sim_code}/personas/{persona_name}",
    f"compressed_storage/{sim_code}/personas/{persona_name}/bootstrap_memory",
    # Fallback to base template if running sim has empty directories
    f"storage/base_the_ville_clean/personas/{persona_name}/bootstrap_memory",
  ]
  
  for path in possible_paths:
    scratch_path = path + "/scratch.json"
    if os.path.exists(scratch_path):
      memory = path
      break
  
  if not memory:
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
      return JsonResponse({"error": f"Persona data not found: {persona_name}"}, status=404)
    return HttpResponse(f"Persona data not found: {persona_name}", status=404)

  try:
    with open(memory + "/scratch.json", encoding="utf-8") as json_file:  
      scratch = json.load(json_file)
  except Exception as e:
    return HttpResponse(f"Error loading scratch.json from {memory}: {e}", status=500)

  try:
    with open(memory + "/spatial_memory.json", encoding="utf-8") as json_file:  
      spatial = json.load(json_file)
  except Exception as e:
    return HttpResponse(f"Error loading spatial_memory.json from {memory}: {e}", status=500)

  try:
    with open(memory + "/associative_memory/nodes.json", encoding="utf-8") as json_file:  
      associative = json.load(json_file)
  except Exception as e:
    return HttpResponse(f"Error loading associative_memory/nodes.json from {memory}: {e}", status=500)

  a_mem_event = []
  a_mem_chat = []
  a_mem_thought = []

  # 处理 associative 可能是空列表或字典的情况
  if isinstance(associative, dict) and associative:
    for count in range(len(associative.keys()), 0, -1): 
      node_id = f"node_{str(count)}"
      node_details = associative.get(node_id)
      if not node_details:
        continue

      if node_details.get("type") == "event":
        a_mem_event += [node_details]

      elif node_details.get("type") == "chat":
        a_mem_chat += [node_details]

      elif node_details.get("type") == "thought":
        a_mem_thought += [node_details]
  
  # 情感统计
  sentiment_stats = {
    "enabled": SENTIMENT_ENABLED,
    "total_chats": 0,
    "positive_count": 0,
    "negative_count": 0,
    "neutral_count": 0,
    "average_score": 0.0,
    "chat_sentiments": []  # 每条对话的情感
  }
  
  if SENTIMENT_ENABLED and a_mem_chat:
    total_score = 0
    for chat in a_mem_chat:
      desc = chat.get("description", "")
      if desc:
        sentiment = analyze_sentiment(desc)
        emoji = "😊" if sentiment["label"] == "positive" else ("😟" if sentiment["label"] == "negative" else "😐")
        sentiment_stats["chat_sentiments"].append({
          "description": desc[:100],
          "label": sentiment["label"],
          "score": sentiment["score"],
          "emoji": emoji
        })
        total_score += sentiment["score"]
        if sentiment["label"] == "positive":
          sentiment_stats["positive_count"] += 1
        elif sentiment["label"] == "negative":
          sentiment_stats["negative_count"] += 1
        else:
          sentiment_stats["neutral_count"] += 1
    
    sentiment_stats["total_chats"] = len(a_mem_chat)
    if sentiment_stats["total_chats"] > 0:
      sentiment_stats["average_score"] = round(total_score / sentiment_stats["total_chats"], 3)
  
  # 如果请求是AJAX，返回JSON格式
  if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
    return JsonResponse({
      "sim_code": sim_code,
      "step": step,
      "persona_name": persona_name, 
      "persona_name_underscore": persona_name_underscore, 
      "scratch": scratch,
      "spatial": spatial,
      "a_mem_event": a_mem_event,
      "a_mem_chat": a_mem_chat,
      "a_mem_thought": a_mem_thought,
      "sentiment_stats": sentiment_stats
    })
  
  context = {"sim_code": sim_code,
             "step": step,
             "persona_name": persona_name, 
             "persona_name_underscore": persona_name_underscore, 
             "scratch": scratch,
             "spatial": spatial,
             "a_mem_event": a_mem_event,
             "a_mem_chat": a_mem_chat,
             "a_mem_thought": a_mem_thought,
             "sentiment_stats": sentiment_stats}
  template = "persona_state/persona_state.html"
  return render(request, template, context)


def path_tester(request):
  context = {}
  template = "path_tester/path_tester.html"
  return render(request, template, context)


def process_environment(request): 
  """
  <FRONTEND to BACKEND> 
  This sends the frontend visual world information to the backend server. 
  It does this by writing the current environment representation to 
  "storage/environment.json" file. 

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse: string confirmation message. 
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:  
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]
  environment = data["environment"]

  with open(f"storage/{sim_code}/environment/{step}.json", "w") as outfile:
    outfile.write(json.dumps(environment, indent=2))

  return HttpResponse("received")


def update_environment(request): 
  """
  <BACKEND to FRONTEND> 
  This sends the backend computation of the persona behavior to the frontend
  visual server. 
  It does this by reading the new movement information from 
  "storage/movement.json" file.

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse
  """
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:  
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]

  response_data = {"<step>": -1}
  if (check_if_file_exists(f"storage/{sim_code}/movement/{step}.json")):
    try:
      with open(f"storage/{sim_code}/movement/{step}.json", encoding='utf-8') as json_file: 
        content = json_file.read()
        if content.strip():  # 确保文件不为空
          response_data = json.loads(content)
          response_data["<step>"] = step
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
      print(f"[views.py] Error reading movement/{step}.json: {e}")
      response_data = {"<step>": -1}

  return JsonResponse(response_data)


def path_tester_update(request): 
  """
  Processing the path and saving it to path_tester_env.json temp storage for 
  conducting the path tester. 

  ARGS:
    request: Django request
  RETURNS: 
    HttpResponse: string confirmation message. 
  """
  data = json.loads(request.body)
  camera = data["camera"]

  with open(f"temp_storage/path_tester_env.json", "w") as outfile:
    outfile.write(json.dumps(camera, indent=2))

  return HttpResponse("received")


def expert_meeting_trigger(request):
  """
  检查专家会议是否触发的API端点
  后端在23:00创建 temp_storage/expert_meeting_trigger.json，前端轮询此接口
  """
  try:
    # 后端 reverie.py 创建的文件路径: temp_storage/expert_meeting_trigger.json
    trigger_file_path = Path(__file__).parent.parent / "temp_storage" / "expert_meeting_trigger.json"
    
    if trigger_file_path.exists():
      # 检查文件是否过期（超过1小时自动删除）
      file_mtime = trigger_file_path.stat().st_mtime
      file_age_seconds = datetime.datetime.now().timestamp() - file_mtime
      if file_age_seconds > 3600:  # 1小时 = 3600秒
        trigger_file_path.unlink()
        return JsonResponse({"triggered": False, "message": "Old trigger file cleaned up"})
      
      with open(trigger_file_path, 'r', encoding='utf-8') as f:
        trigger_data = json.load(f)
      
      # 返回完整的触发数据（包含speeches、status、pending_speaker）
      response_data = {
        "triggered": True,
        "timestamp": trigger_data.get("timestamp", ""),
        "action": trigger_data.get("action", "show_expert_conversation"),
        "topic": trigger_data.get("topic", "校园食品安全专家会议"),
        "speeches": trigger_data.get("speeches", []),
        "round_summaries": trigger_data.get("round_summaries", []),
        "status": trigger_data.get("status", "completed"),
        "pending_speaker": trigger_data.get("pending_speaker"),
      }
      if trigger_data.get("error"):
        response_data["error"] = trigger_data.get("error")
      
      return JsonResponse(response_data)
    else:
      # 文件不存在，会议未触发
      return JsonResponse({"triggered": False})
      
  except Exception as e:
    return JsonResponse({"triggered": False, "error": str(e)})


@csrf_exempt
def dismiss_expert_meeting(request):
  """
  关闭专家会议弹窗时：
  1. 先把会议内容保存到历史记录文件
  2. 再删除触发文件
  支持 GET 和 POST（sendBeacon 用 POST）
  """
  try:
    trigger_file_path = Path(__file__).parent.parent / "temp_storage" / "expert_meeting_trigger.json"
    history_dir = Path(__file__).parent.parent / "temp_storage" / "expert_meeting_history"
    
    if trigger_file_path.exists():
      # 读取触发文件内容
      with open(trigger_file_path, 'r', encoding='utf-8') as f:
        trigger_data = json.load(f)
      
      # 如果有实际的会议内容，保存到历史记录
      if trigger_data.get("speeches"):
        # 创建历史目录
        history_dir.mkdir(parents=True, exist_ok=True)
        
        # 用时间戳命名历史文件
        timestamp = trigger_data.get("timestamp", "unknown")
        # 清理时间戳中的特殊字符
        safe_timestamp = str(timestamp).replace(":", "-").replace("T", "_")[:19]
        history_file = history_dir / f"meeting_{safe_timestamp}.json"
        
        # 保存历史记录
        with open(history_file, 'w', encoding='utf-8') as f:
          json.dump(trigger_data, f, ensure_ascii=False, indent=2)
      
      # 删除触发文件
      trigger_file_path.unlink()
      return JsonResponse({"success": True, "message": "Meeting saved to history, trigger file deleted"})
    else:
      return JsonResponse({"success": True, "message": "File already deleted"})
      
  except Exception as e:
    return JsonResponse({"success": False, "error": str(e)})





