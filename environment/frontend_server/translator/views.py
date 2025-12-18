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
import time

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
from . import start_time_config

# 情感分析模块
try:
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', 'generative_agents-main', 'reverie', 'backend_server'))
    from sentiment.sentiment_analysis import analyze_sentiment, get_sentiment_summary
    SENTIMENT_ENABLED = True
except ImportError:
    SENTIMENT_ENABLED = False

def landing(request):
  """
  初始界面：可以设置世界的开始时间
  """
  meta_path = "storage/base_the_ville_clean/reverie/meta.json"
  
  # 读取当前的 meta.json 配置
  current_start_date = None
  current_curr_time = None
  initial_date_iso = None
  initial_time_iso = None
  
  if os.path.exists(meta_path):
    try:
      with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
        current_start_date = meta.get("start_date", "")
        current_curr_time = meta.get("curr_time", "")
        
        # 解析日期和时间，用于表单默认值
        if current_start_date:
          try:
            # 解析 "February 13, 2023" 格式
            dt = datetime.datetime.strptime(current_start_date, "%B %d, %Y")
            initial_date_iso = dt.strftime("%Y-%m-%d")
          except:
            pass
        
        if current_curr_time:
          try:
            # 解析 "February 13, 2023, 17:00:00" 格式
            dt = datetime.datetime.strptime(current_curr_time, "%B %d, %Y, %H:%M:%S")
            initial_time_iso = dt.strftime("%H:%M")
            if not initial_date_iso:
              initial_date_iso = dt.strftime("%Y-%m-%d")
          except:
            pass
    except Exception as e:
      print(f"[landing] Error reading meta.json: {e}")
  
  # 处理 POST 请求：保存开始时间
  if request.method == "POST":
    error = None
    message = None
    
    try:
      start_date_str = request.POST.get("start_date", "").strip()
      start_time_str = request.POST.get("start_time", "00:00").strip()
      
      if not start_date_str:
        error = "请选择开始日期"
      else:
        # 解析表单提交的日期时间（YYYY-MM-DD 和 HH:MM 格式）
        date_part = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        time_part = datetime.datetime.strptime(start_time_str, "%H:%M") if start_time_str else datetime.datetime.strptime("00:00", "%H:%M")
        
        # 转换为项目使用的格式
        formatted_date = date_part.strftime("%B %d, %Y")  # "February 13, 2023"
        formatted_time = time_part.strftime("%H:%M:%S")   # "17:00:00"
        formatted_curr_time = f"{formatted_date}, {formatted_time}"
        
        # 读取现有的 meta.json
        if os.path.exists(meta_path):
          with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        else:
          meta = {}
        
        # 更新日期和时间
        meta["start_date"] = formatted_date
        meta["curr_time"] = formatted_curr_time
        
        # 写回文件
        os.makedirs(os.path.dirname(meta_path), exist_ok=True)
        with open(meta_path, 'w', encoding='utf-8') as f:
          json.dump(meta, f, indent=2, ensure_ascii=False)
        
        # 额外写入 temp_storage，便于后端在 fork 时立即读取最新时间
        try:
          pending_path = os.path.join("temp_storage", "pending_start_time.json")
          os.makedirs(os.path.dirname(pending_path), exist_ok=True)
          with open(pending_path, 'w', encoding='utf-8') as f:
            json.dump({
              "start_date": formatted_date,
              "curr_time": formatted_curr_time,
              "saved_at": datetime.datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        except Exception as e:
          # 不影响主流程，只记录日志
          print(f"[landing] 写入 pending_start_time 失败: {e}")
        
        message = f"开始时间已更新为 {formatted_date} {formatted_time}。下次运行新仿真时将使用此时间。"
        current_start_date = formatted_date
        current_curr_time = formatted_curr_time
        initial_date_iso = start_date_str
        initial_time_iso = start_time_str
        
    except ValueError as e:
      error = f"日期时间格式错误：{str(e)}"
    except Exception as e:
      error = f"保存失败：{str(e)}"
      import traceback
      print(f"[landing] Error saving: {traceback.format_exc()}")
  
  context = {
    "current_start_date": current_start_date,
    "current_curr_time": current_curr_time,
    "initial_date_iso": initial_date_iso or "",
    "initial_time_iso": initial_time_iso or "00:00",
    "error": error if 'error' in locals() else None,
    "message": message if 'message' in locals() else None,
  }
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
  with open(meta_file, encoding="utf-8") as json_file: 
    meta = json.load(json_file)

  sec_per_step = meta["sec_per_step"]
  start_datetime = datetime.datetime.strptime(meta["start_date"] + " 00:00:00", 
                                              '%B %d, %Y %H:%M:%S')
  for i in range(step): 
    start_datetime += datetime.timedelta(seconds=sec_per_step)
  start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%S")

  # Loading the movement file
  raw_all_movement = dict()
  with open(move_file, encoding="utf-8") as json_file: 
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

  with open(f_curr_sim_code, encoding="utf-8") as json_file:  
    sim_code = json.load(json_file)["sim_code"]
  
  with open(f_curr_step, encoding="utf-8") as json_file:  
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
  with open(curr_json, encoding="utf-8") as json_file:  
    persona_init_pos_dict = json.load(json_file)
    for key, val in persona_init_pos_dict.items(): 
      if key in persona_names_set: 
        persona_init_pos += [[key, val["x"], val["y"]]]

  # 读取初始时间
  initial_time_str = None
  try:
    meta_path = f"storage/{sim_code}/reverie/meta.json"
    if os.path.exists(meta_path):
      with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
      initial_time_str = meta.get("curr_time", None)
  except Exception as e:
    print(f"[home] Error reading meta.json for initial time: {e}")

  context = {"sim_code": sim_code,
             "step": step, 
             "persona_names": persona_names,
             "persona_init_pos": persona_init_pos,
             "initial_time": initial_time_str,
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
  with open(curr_json, encoding="utf-8") as json_file:  
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


# 用于节流日志输出的全局变量
_last_update_log_time = 0

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
  global _last_update_log_time
  
  # f_curr_sim_code = "temp_storage/curr_sim_code.json"
  # with open(f_curr_sim_code) as json_file:  
  #   sim_code = json.load(json_file)["sim_code"]

  data = json.loads(request.body)
  step = data["step"]
  sim_code = data["sim_code"]

  # 节流日志输出：每秒只打印一次
  current_time = time.time()
  if current_time - _last_update_log_time >= 1.0:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [update_environment] Step {step}, sim_code: {sim_code}")
    _last_update_log_time = current_time

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


# ============================================================================
# 线上舆论 API
# ============================================================================

def online_forum(request):
  """线上舆论广场页面"""
  context = {
    "sim_code": request.GET.get("sim_code", "")
  }
  return render(request, "online_forum/online_forum.html", context)


def get_online_posts(request):
  """获取线上舆论帖子"""
  try:
    # 尝试从当前运行的 simulation 读取
    sim_code = request.GET.get("sim_code", "")
    
    # 构建可能的路径
    paths_to_try = []
    
    if sim_code:
      paths_to_try.append(f"storage/{sim_code}/online_opinions/posts.json")
    
    # 默认路径
    paths_to_try.append("storage/base_the_ville_clean/online_opinions/posts.json")
    
    posts_data = None
    for path in paths_to_try:
      if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
          posts_data = json.load(f)
        break
    
    if posts_data is None:
      return JsonResponse({
        "posts": [],
        "total": 0,
        "message": "舆论库尚未创建"
      })
    
    return JsonResponse({
      "posts": posts_data.get("posts", []),
      "total": len(posts_data.get("posts", [])),
      "metadata": posts_data.get("metadata", {})
    })
    
  except Exception as e:
    return JsonResponse({
      "posts": [],
      "total": 0,
      "error": str(e)
    })


def sentiment_timeline(request):
  """按日期汇总线上舆论的情感趋势（便于前端绘制时间序列）"""
  sim_code = request.GET.get("sim_code", "")
  paths_to_try = []

  if sim_code:
    paths_to_try.append(f"storage/{sim_code}/online_opinions/posts.json")
  paths_to_try.append("storage/base_the_ville_clean/online_opinions/posts.json")

  posts_data = None
  source_path = None
  for path in paths_to_try:
    if os.path.exists(path):
      with open(path, 'r', encoding='utf-8') as f:
        posts_data = json.load(f)
      source_path = path
      break

  if posts_data is None:
    return JsonResponse({
      "enabled": SENTIMENT_ENABLED,
      "timeline": [],
      "message": "舆论库尚未创建"
    })

  buckets = {}
  for post in posts_data.get("posts", []):
    ts = post.get("timestamp")
    content = post.get("content", "")

    # 解析日期（忽略无效时间戳）
    try:
      dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") if ts else None
    except Exception:
      dt = None

    if not dt:
      continue

    date_key = dt.strftime("%Y-%m-%d")
    bucket = buckets.setdefault(date_key, {
      "date": date_key,
      "total": 0,
      "positive": 0,
      "negative": 0,
      "neutral": 0,
      "scores": []
    })

    if SENTIMENT_ENABLED:
      result = analyze_sentiment(content)
      label = result.get("label", "neutral")
      score = result.get("score", 0.0)
    else:
      label = "neutral"
      score = 0.0

    bucket["total"] += 1
    if label == "positive":
      bucket["positive"] += 1
    elif label == "negative":
      bucket["negative"] += 1
    else:
      bucket["neutral"] += 1

    bucket["scores"].append(score)

  # 构建排序后的时间序列
  timeline = []
  for date_key in sorted(buckets.keys()):
    bucket = buckets[date_key]
    avg_score = round(sum(bucket["scores"]) / len(bucket["scores"]), 3) if bucket["scores"] else 0.0
    timeline.append({
      "date": date_key,
      "total": bucket["total"],
      "positive": bucket["positive"],
      "negative": bucket["negative"],
      "neutral": bucket["neutral"],
      "average_score": avg_score
    })

  return JsonResponse({
    "enabled": SENTIMENT_ENABLED,
    "timeline": timeline,
    "source": source_path,
    "total_posts": len(posts_data.get("posts", []))
  })


@csrf_exempt
def post_online_opinion(request):
  """发表线上舆论（测试用）"""
  if request.method != "POST":
    return JsonResponse({"error": "仅支持 POST 请求"}, status=405)
  
  try:
    data = json.loads(request.body)
    
    online_name = data.get("online_name", "匿名用户")
    real_name = data.get("real_name", "")
    content = data.get("content", "")
    
    if not content:
      return JsonResponse({"error": "内容不能为空"}, status=400)
    
    # 读取现有帖子
    path = "storage/base_the_ville_clean/online_opinions/posts.json"
    
    if os.path.exists(path):
      with open(path, 'r', encoding='utf-8') as f:
        posts_data = json.load(f)
    else:
      posts_data = {"posts": [], "metadata": {}}
    
    # 创建新帖子
    new_post = {
      "id": len(posts_data["posts"]) + 1,
      "online_name": online_name,
      "real_name": real_name,
      "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
      "content": content,
      "topic": "幼儿园食物中毒事件"
    }
    
    posts_data["posts"].append(new_post)
    posts_data["metadata"]["total_posts"] = len(posts_data["posts"])
    
    # 保存
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
      json.dump(posts_data, f, ensure_ascii=False, indent=2)
    
    return JsonResponse({"success": True, "post": new_post})
    
  except Exception as e:
    return JsonResponse({"error": str(e)}, status=500)


# ============================================================================
# 独立开始时间设置页面
# ============================================================================

def start_time_setup(request):
  """
  独立的开始时间设置页面
  使用独立的 JSON 文件存储，不依赖 base_the_ville_clean 的 meta.json
  """
  error = None
  message = None
  current_start_date = None
  current_curr_time = None
  initial_date_iso = None
  initial_time_iso = None
  
  # 读取当前配置
  start_date, curr_time = start_time_config.load_start_time()
  if start_date and curr_time:
    current_start_date = start_date
    current_curr_time = curr_time
    try:
      # 解析日期和时间，用于表单默认值
      dt = datetime.datetime.strptime(curr_time, "%B %d, %Y, %H:%M:%S")
      initial_date_iso = dt.strftime("%Y-%m-%d")
      initial_time_iso = dt.strftime("%H:%M")
    except:
      # 如果读取失败，使用默认值
      default_date, default_time = start_time_config.get_default_time()
      try:
        dt = datetime.datetime.strptime(default_time, "%B %d, %Y, %H:%M:%S")
        initial_date_iso = dt.strftime("%Y-%m-%d")
        initial_time_iso = dt.strftime("%H:%M")
      except:
        initial_date_iso = "2023-02-13"
        initial_time_iso = "00:00"
  else:
    # 如果没有配置，使用默认值
    default_date, default_time = start_time_config.get_default_time()
    try:
      dt = datetime.datetime.strptime(default_time, "%B %d, %Y, %H:%M:%S")
      initial_date_iso = dt.strftime("%Y-%m-%d")
      initial_time_iso = dt.strftime("%H:%M")
    except:
      initial_date_iso = "2023-02-13"
      initial_time_iso = "00:00"
  
  # 读取模型配置
  use_local_model, local_model_name = start_time_config.load_model_config()
  if use_local_model is None:
    use_local_model = False  # 默认关闭本地模型，使用云端API
  if not local_model_name:
    local_model_name = "deepseek-R1:8b"  # 默认模型名称（仅在开启时使用）
  
  # 处理 POST 请求：保存开始时间和模型配置
  if request.method == "POST":
    try:
      start_date_str = request.POST.get("start_date", "").strip()
      start_time_str = request.POST.get("start_time", "00:00").strip()
      
      # 读取模型配置
      # checkbox 如果选中会发送 "true" 或 "on"，如果未选中则不会发送该字段
      use_local_model_post = request.POST.get("use_local_model", "")
      use_local_model_bool = use_local_model_post.lower() in ["true", "on"] or use_local_model_post == "true"
      local_model_name_post = request.POST.get("local_model_name", "").strip()
      
      # 调试信息
      print(f"[start_time_setup] 表单提交 - use_local_model_post: '{use_local_model_post}', use_local_model_bool: {use_local_model_bool}")
      print(f"[start_time_setup] 表单提交 - local_model_name_post: '{local_model_name_post}'")
      
      if not start_date_str:
        error = "请选择开始日期"
      else:
        # 解析表单提交的日期时间（YYYY-MM-DD 和 HH:MM 格式）
        date_part = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        time_part = datetime.datetime.strptime(start_time_str, "%H:%M") if start_time_str else datetime.datetime.strptime("00:00", "%H:%M")
        
        # 转换为项目使用的格式
        formatted_date = date_part.strftime("%B %d, %Y")  # "February 13, 2023"
        formatted_time = time_part.strftime("%H:%M:%S")   # "17:00:00"
        formatted_curr_time = f"{formatted_date}, {formatted_time}"
        
        # 保存开始时间
        if start_time_config.save_start_time(formatted_date, formatted_curr_time):
          # 保存模型配置
          if use_local_model_bool:
            # 如果开关打开，必须提供模型名称
            if local_model_name_post:
              start_time_config.save_model_config(True, local_model_name_post)
            else:
              # 如果模型名称为空，使用默认值
              start_time_config.save_model_config(True, "deepseek-R1:8b")
          else:
            # 如果开关关闭，保存为 False，不保存模型名称
            start_time_config.save_model_config(False, "")
          
          # 保存成功后重定向到 simulator_home
          return redirect('home')
        else:
          error = "保存失败，请检查文件权限"
        
    except ValueError as e:
      error = f"日期时间格式错误：{str(e)}"
    except Exception as e:
      error = f"保存失败：{str(e)}"
      import traceback
      print(f"[start_time_setup] Error: {traceback.format_exc()}")
  
  context = {
    "current_start_date": current_start_date,
    "current_curr_time": current_curr_time,
    "initial_date_iso": initial_date_iso or "2023-02-13",
    "initial_time_iso": initial_time_iso or "00:00",
    "use_local_model": use_local_model,
    "local_model_name": local_model_name,
    "error": error,
    "message": message,
  }
  template = "start_time_setup/start_time_setup.html"
  return render(request, template, context)


@csrf_exempt
def check_start_time_configured(request):
  """检查开始时间是否已配置（用于启动脚本）"""
  start_date, curr_time = start_time_config.load_start_time()
  if start_date and curr_time:
    return JsonResponse({
      "configured": True,
      "start_date": start_date,
      "curr_time": curr_time
    })
  else:
    return JsonResponse({
      "configured": False,
      "message": "开始时间未配置"
    })


def opinion_statistics_chart(request):
  """
  收集全部舆论并生成统计图表数据
  返回：数量统计（直方图）+ 情感统计（线型图）
  """
  try:
    sim_code = request.GET.get("sim_code", "")
    paths_to_try = []
    
    if sim_code:
      paths_to_try.append(f"storage/{sim_code}/online_opinions/posts.json")
    paths_to_try.append("storage/base_the_ville_clean/online_opinions/posts.json")
    
    posts_data = None
    for path in paths_to_try:
      if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
          posts_data = json.load(f)
        break
    
    if posts_data is None:
      return JsonResponse({
        "success": True,
        "enabled": SENTIMENT_ENABLED,
        "message": "舆论库尚未创建",
        "chart_data": {
          "dates": [],
          "counts": {"total": [], "positive": [], "negative": [], "neutral": []},
          "sentiment_scores": []
        },
        "statistics": {
          "total_posts": 0,
          "total_positive": 0,
          "total_negative": 0,
          "total_neutral": 0,
          "average_sentiment": 0.0
        }
      })
    
    posts = posts_data.get("posts", [])
    
    # 按日期分组统计
    date_buckets = {}
    for post in posts:
      ts = post.get("timestamp", "")
      content = post.get("content", "")
      
      try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") if ts else None
      except Exception:
        dt = None
      
      if not dt:
        continue
      
      date_key = dt.strftime("%Y-%m-%d")
      bucket = date_buckets.setdefault(date_key, {
        "date": date_key,
        "total": 0,
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "scores": []
      })
      
      # 情感分析
      if SENTIMENT_ENABLED:
        result = analyze_sentiment(content)
        label = result.get("label", "neutral")
        score = result.get("score", 0.0)
      else:
        label = "neutral"
        score = 0.0
      
      bucket["total"] += 1
      if label == "positive":
        bucket["positive"] += 1
      elif label == "negative":
        bucket["negative"] += 1
      else:
        bucket["neutral"] += 1
      
      bucket["scores"].append(score)
    
    # 构建图表数据（按日期排序）
    sorted_dates = sorted(date_buckets.keys())
    chart_data = {
      "dates": sorted_dates,
      "counts": {
        "total": [],
        "positive": [],
        "negative": [],
        "neutral": []
      },
      "sentiment_scores": []
    }
    
    for date_key in sorted_dates:
      bucket = date_buckets[date_key]
      chart_data["counts"]["total"].append(bucket["total"])
      chart_data["counts"]["positive"].append(bucket["positive"])
      chart_data["counts"]["negative"].append(bucket["negative"])
      chart_data["counts"]["neutral"].append(bucket["neutral"])
      
      # 计算平均情感分数
      avg_score = round(sum(bucket["scores"]) / len(bucket["scores"]), 3) if bucket["scores"] else 0.0
      chart_data["sentiment_scores"].append(avg_score)
    
    # 总体统计
    total_stats = {
      "total_posts": len(posts),
      "total_positive": sum(bucket["positive"] for bucket in date_buckets.values()),
      "total_negative": sum(bucket["negative"] for bucket in date_buckets.values()),
      "total_neutral": sum(bucket["neutral"] for bucket in date_buckets.values()),
      "average_sentiment": round(
        sum(chart_data["sentiment_scores"]) / len(chart_data["sentiment_scores"]) 
        if chart_data["sentiment_scores"] else 0.0, 
        3
      )
    }
    
    return JsonResponse({
      "enabled": SENTIMENT_ENABLED,
      "chart_data": chart_data,
      "statistics": total_stats,
      "success": True
    })
    
  except Exception as e:
    import traceback
    print(f"[opinion_statistics_chart] Error: {traceback.format_exc()}")
    return JsonResponse({
      "success": False,
      "enabled": False,
      "error": str(e),
      "message": "加载数据时发生错误: " + str(e),
      "chart_data": {
        "dates": [],
        "counts": {"total": [], "positive": [], "negative": [], "neutral": []},
        "sentiment_scores": []
      },
      "statistics": {
        "total_posts": 0,
        "total_positive": 0,
        "total_negative": 0,
        "total_neutral": 0,
        "average_sentiment": 0.0
      }
    })

