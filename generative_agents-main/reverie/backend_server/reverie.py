"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reverie.py
Description: This is the main program for running generative agent simulations
that defines the ReverieServer class. This class maintains and records all  
states related to the simulation. The primary mode of interaction for those  
running the simulation should be through the open_server function, which  
enables the simulator to input command-line prompts for running and saving  
the simulation, among other tasks.

Release note (June 14, 2023) -- Reverie implements the core simulation 
mechanism described in my paper entitled "Generative Agents: Interactive 
Simulacra of Human Behavior." If you are reading through these lines after 
having read the paper, you might notice that I use older terms to describe 
generative agents and their cognitive modules here. Most notably, I use the 
term "personas" to refer to generative agents, "associative memory" to refer 
to the memory stream, and "reverie" to refer to the overarching simulation 
framework.
"""
import json
import numpy
import datetime
import pickle
import time
import math
import os
import shutil
import traceback
import webbrowser

from selenium import webdriver

from global_methods import *
from utils import *
from maze import *
from persona.persona import *
from path_finder import path_finder
from utils import collision_block_id
from expert_init import (
  inject_food_poisoning_event,
  generate_and_broadcast_public_opinion,
)
from opinion_collector import collect_and_inject_opinions
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
# 添加expert_system工具目录到路径
# 从当前文件位置: generative_agents-main/generative_agents-main/reverie/backend_server/reverie.py
# 需要回到: generative_agents-main/seminar_expert/expert_system
expert_system_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'seminar_expert', 'expert_system')
expert_system_path = os.path.abspath(expert_system_path)  # 转换为绝对路径
sys.path.append(expert_system_path)

print(f"[Reverie] 尝试从路径加载专家模块: {expert_system_path}")
print(f"[Reverie] 路径是否存在: {os.path.exists(expert_system_path)}")

try:
    from expert_position_monitor import ExpertPositionMonitor
    EXPERT_MONITOR_AVAILABLE = True
    print("[Reverie] 专家位置监控模块已加载")
except ImportError as e:
    print(f"[Reverie] 专家位置监控模块加载失败: {e}")
    print(f"[Reverie] 当前 sys.path: {sys.path[-3:]}")  # 显示最后3个路径
    EXPERT_MONITOR_AVAILABLE = False
    ExpertPositionMonitor = None

##############################################################################
#                                  REVERIE                                   #
##############################################################################

class ReverieServer: 
  def __init__(self, 
               fork_sim_code,
               sim_code):
    # FORKING FROM A PRIOR SIMULATION:
    # <fork_sim_code> indicates the simulation we are forking from. 
    # Interestingly, all simulations must be forked from some initial 
    # simulation, where the first simulation is "hand-crafted".
    self.fork_sim_code = fork_sim_code
    fork_folder = f"{fs_storage}/{self.fork_sim_code}"

    # <sim_code> indicates our current simulation. The first step here is to 
    # copy everything that's in <fork_sim_code>, but edit its 
    # reverie/meta/json's fork variable. 
    self.sim_code = sim_code
    sim_folder = f"{fs_storage}/{self.sim_code}"
    copyanything(fork_folder, sim_folder)

    # 清理旧 environment：保留 0.json，删除其余步数，避免沿用旧世界中缺少专家的帧
    env_folder = f"{sim_folder}/environment"
    if os.path.isdir(env_folder):
      for fname in os.listdir(env_folder):
        if fname.endswith(".json") and fname.split(".")[0] != "0":
          try:
            os.remove(os.path.join(env_folder, fname))
          except OSError:
            pass

    # 重置 movement 目录，确保当前 run 从空白 movement 开始
    movement_folder = f"{sim_folder}/movement"
    if os.path.isdir(movement_folder):
      try:
        shutil.rmtree(movement_folder)
      except OSError:
        pass
    os.makedirs(movement_folder, exist_ok=True)

    with open(f"{sim_folder}/reverie/meta.json") as json_file:  
      reverie_meta = json.load(json_file)

    # Fork 出新世界线时，不仅要记录 fork_sim_code，
    # 还要把 step 重置为 0，确保从 environment/0.json 开始推进。
    reverie_meta["fork_sim_code"] = fork_sim_code
    reverie_meta["step"] = 0

    # 设置初始时间：如果 meta.json 中已有手动设置的 curr_time（非空），则保留它；
    # 否则，如果是从 base_the_ville_clean fork 出来的世界线，默认从 00:00:00 开始。
    # 这样前端在 landing 页面设置的时间会被保留，不会被覆盖。
    # 注意：这里检查的是复制过来的 meta.json 中的 curr_time，如果前端已经设置过，应该已经存在。
    existing_curr_time = reverie_meta.get("curr_time", "").strip()
    if not existing_curr_time:
      # 只有在 curr_time 不存在或为空时，才设置默认值
      if fork_sim_code == "base_the_ville_clean":
        date_str = reverie_meta.get("start_date", "February 13, 2023")
        reverie_meta["curr_time"] = f"{date_str}, 00:00:00"
      # 如果 fork_sim_code 不是 base_the_ville_clean，且没有 curr_time，则从 start_date 的 00:00:00 开始
      elif "start_date" in reverie_meta:
        date_str = reverie_meta.get("start_date", "February 13, 2023")
        reverie_meta["curr_time"] = f"{date_str}, 00:00:00"
    else:
      # 如果已有 curr_time，保留它（前端设置的时间会被保留）
      print(f"[Reverie] 保留已设置的初始时间: {existing_curr_time}")

    with open(f"{sim_folder}/reverie/meta.json", "w") as outfile: 
      outfile.write(json.dumps(reverie_meta, indent=2))

    # LOADING REVERIE'S GLOBAL VARIABLES
    # The start datetime of the Reverie: 
    # <start_datetime> is the datetime instance for the start datetime of 
    # the Reverie instance. Once it is set, this is not really meant to 
    # change. It takes a string date in the following example form: 
    # "June 25, 2022"
    # e.g., ...strptime(June 25, 2022, "%B %d, %Y")
    self.start_time = datetime.datetime.strptime(
                        f"{reverie_meta['start_date']}, 00:00:00",  
                        "%B %d, %Y, %H:%M:%S")
    # <curr_time> is the datetime instance that indicates the game's current
    # time. This gets incremented by <sec_per_step> amount everytime the world
    # progresses (that is, everytime curr_env_file is recieved). 
    self.curr_time = datetime.datetime.strptime(reverie_meta['curr_time'], 
                                                "%B %d, %Y, %H:%M:%S")
    # <sec_per_step> denotes the number of seconds in game time that each 
    # step moves foward. 
    self.sec_per_step = reverie_meta['sec_per_step']
    
    # <maze> is the main Maze instance. Note that we pass in the maze_name
    # (e.g., "double_studio") to instantiate Maze. 
    # e.g., Maze("double_studio")
    self.maze = Maze(reverie_meta['maze_name'])
    
    # <step> denotes the number of steps that our game has taken. A step here
    # literally translates to the number of moves our personas made in terms
    # of the number of tiles. 
    # 这里使用我们在上面刚写回 meta.json 的 step（已被强制设为 0），
    # 避免继承旧世界的大 step 值导致无法找到对应 environment/<step>.json。
    self.step = reverie_meta['step']

    # SETTING UP PERSONAS IN REVERIE
    # <personas> is a dictionary that takes the persona's full name as its 
    # keys, and the actual persona instance as its values.
    # This dictionary is meant to keep track of all personas who are part of
    # the Reverie instance. 
    # e.g., ["Isabella Rodriguez"] = Persona("Isabella Rodriguezs")
    self.personas = dict()
    # <personas_tile> is a dictionary that contains the tile location of
    # the personas (!-> NOT px tile, but the actual tile coordinate).
    # The tile take the form of a set, (row, col). 
    # e.g., ["Isabella Rodriguez"] = (58, 39)
    self.personas_tile = dict()
    
    # # <persona_convo_match> is a dictionary that describes which of the two
    # # personas are talking to each other. It takes a key of a persona's full
    # # name, and value of another persona's full name who is talking to the 
    # # original persona. 
    # # e.g., dict["Isabella Rodriguez"] = ["Maria Lopez"]
    # self.persona_convo_match = dict()
    # # <persona_convo> contains the actual content of the conversations. It
    # # takes as keys, a pair of persona names, and val of a string convo. 
    # # Note that the key pairs are *ordered alphabetically*. 
    # # e.g., dict[("Adam Abraham", "Zane Xu")] = "Adam: baba \n Zane:..."
    # self.persona_convo = dict()

    # Loading in all personas. 
    init_env_file = f"{sim_folder}/environment/{str(self.step)}.json"
    init_env = json.load(open(init_env_file))
    for persona_name in reverie_meta['persona_names']: 
      # 在某些场景下，meta.json 中列出的 persona 可能尚未在
      # environment/0.json 中配置初始位置（例如刚新增的专家）。
      # 为避免 KeyError，这里如果 init_env 中没有该 persona，就跳过。
      if persona_name not in init_env:
        continue

      persona_folder = f"{sim_folder}/personas/{persona_name}"
      p_x = init_env[persona_name]["x"]
      p_y = init_env[persona_name]["y"]
      curr_persona = Persona(persona_name, persona_folder)

      # 每次 fork 新世界时，只继承身份和长期记忆，
      # 但当天状态 / 日程不应沿用旧世界，否则会出现“整天睡觉”的计划。
      # 因此这里显式重置与“今天”相关的 scratch 状态，让新世界从当前
      # Reverie 的 curr_time 作为一个全新的 "First day" 重新规划日程。
      s = curr_persona.scratch
      s.curr_time = None
      
      # 专家保留daily_plan_req，普通agent清空
      experts_and_moderator = [
        "Public Health Expert",
        "Market Supervision Expert", 
        "Education Bureau Representative",
        "Meeting Moderator"
      ]
      if curr_persona.name not in experts_and_moderator:
        s.daily_plan_req = None
      
      s.daily_req = []
      s.f_daily_schedule = []
      s.f_daily_schedule_hourly_org = []

      # 同时清空正在进行中的动作、路径和对话，让人物从一个干净的
      # 状态开始新一天的行动。
      s.act_address = None
      s.act_start_time = None
      s.act_duration = None
      s.act_description = None
      s.act_pronunciatio = None
      s.act_event = (s.name, None, None)

      s.act_obj_description = None
      s.act_obj_pronunciatio = None
      s.act_obj_event = (s.name, None, None)

      s.chatting_with = None
      s.chat = None
      s.chatting_with_buffer = dict()
      s.chatting_end_time = None

      s.act_path_set = False
      s.planned_path = []

      # 在初始化时为每个 persona 注入一次校园食物中毒事件的长期记忆
      inject_food_poisoning_event(curr_persona, self.curr_time)

      self.personas[persona_name] = curr_persona
      self.personas_tile[persona_name] = (p_x, p_y)
      self.maze.tiles[p_y][p_x]["events"].add(curr_persona.scratch
                                              .get_curr_event_and_desc())

    # REVERIE SETTINGS PARAMETERS:  
    # <server_sleep> denotes the amount of time that our while loop rests each
    # cycle; this is to not kill our machine. 
    self.server_sleep = 0.1
    
    # EXPERT POSITION MONITOR:
    # Initialize expert position monitor for 23:00 trigger
    if EXPERT_MONITOR_AVAILABLE:
      self.expert_monitor = ExpertPositionMonitor(f"{fs_storage}/{self.sim_code}")
      self.expert_monitor_started = False
    else:
      self.expert_monitor = None
      self.expert_monitor_started = False

    # SIGNALING THE FRONTEND SERVER: 
    # curr_sim_code.json contains the current simulation code, and
    # curr_step.json contains the current step of the simulation. These are 
    # used to communicate the code and step information to the frontend. 
    # Note that step file is removed as soon as the frontend opens up the 
    # simulation. 
    curr_sim_code = dict()
    curr_sim_code["sim_code"] = self.sim_code
    with open(f"{fs_temp_storage}/curr_sim_code.json", "w") as outfile: 
      outfile.write(json.dumps(curr_sim_code, indent=2))
    
    curr_step = dict()
    curr_step["step"] = self.step
    with open(f"{fs_temp_storage}/curr_step.json", "w") as outfile: 
      outfile.write(json.dumps(curr_step, indent=2))

    # 尝试在本机浏览器中自动打开前端页面，方便直接查看仿真结果。
    # （已改为仅由 run_project_autotick.bat 在外部打开一次浏览器，
    #  避免重复打开多个 home 窗口。如果需要恢复自动打开功能，可以
    #  去掉下面这段注释。）
    # try:
    #   webbrowser.open("http://127.0.0.1:8000")
    #   webbrowser.open("http://127.0.0.1:8000/simulator_home")
    # except Exception:
    #   # 打不开浏览器不影响后端主循环
    #   pass

    # 记录上一次为专家生成民众舆论摘要的日期，避免同一天重复生成多次。
    self.last_public_opinion_date = None


  def save(self): 
    """
    Save all Reverie progress -- this includes Reverie's global state as well
    as all the personas.  

    INPUT
      None
    OUTPUT 
      None
      * Saves all relevant data to the designated memory directory
    """
    # <sim_folder> points to the current simulation folder.
    sim_folder = f"{fs_storage}/{self.sim_code}"

    # Save Reverie meta information.
    reverie_meta = dict() 
    reverie_meta["fork_sim_code"] = self.fork_sim_code
    reverie_meta["start_date"] = self.start_time.strftime("%B %d, %Y")
    reverie_meta["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")
    reverie_meta["sec_per_step"] = self.sec_per_step
    reverie_meta["maze_name"] = self.maze.maze_name
    reverie_meta["persona_names"] = list(self.personas.keys())
    reverie_meta["step"] = self.step
    reverie_meta_f = f"{sim_folder}/reverie/meta.json"
    with open(reverie_meta_f, "w") as outfile: 
      outfile.write(json.dumps(reverie_meta, indent=2))

    # Save the personas.
    for persona_name, persona in self.personas.items(): 
      save_folder = f"{sim_folder}/personas/{persona_name}/bootstrap_memory"
      persona.save(save_folder)


  def start_path_tester_server(self): 
    """
    Starts the path tester server. This is for generating the spatial memory
    that we need for bootstrapping a persona's state. 

    To use this, you need to open server and enter the path tester mode, and
    open the front-end side of the browser. 

    INPUT 
      None
    OUTPUT 
      None
      * Saves the spatial memory of the test agent to the path_tester_env.json
        of the temp storage. 
    """
    def print_tree(tree): 
      def _print_tree(tree, depth):
        dash = " >" * depth

        if type(tree) == type(list()): 
          if tree:
            print (dash, tree)
          return 

        for key, val in tree.items(): 
          if key: 
            print (dash, key)
          _print_tree(val, depth+1)
      
      _print_tree(tree, 0)

    # <curr_vision> is the vision radius of the test agent. Recommend 8 as 
    # our default. 
    curr_vision = 8
    # <s_mem> is our test spatial memory. 
    s_mem = dict()

    # The main while loop for the test agent. 
    while (True): 
      try: 
        curr_dict = {}
        tester_file = fs_temp_storage + "/path_tester_env.json"
        if check_if_file_exists(tester_file): 
          with open(tester_file) as json_file: 
            curr_dict = json.load(json_file)
            os.remove(tester_file)
          
          # Current camera location
          curr_sts = self.maze.sq_tile_size
          curr_camera = (int(math.ceil(curr_dict["x"]/curr_sts)), 
                         int(math.ceil(curr_dict["y"]/curr_sts))+1)
          curr_tile_det = self.maze.access_tile(curr_camera)

          # Initiating the s_mem
          world = curr_tile_det["world"]
          if curr_tile_det["world"] not in s_mem: 
            s_mem[world] = dict()

          # Iterating throughn the nearby tiles.
          nearby_tiles = self.maze.get_nearby_tiles(curr_camera, curr_vision)
          for i in nearby_tiles: 
            i_det = self.maze.access_tile(i)
            if (curr_tile_det["sector"] == i_det["sector"] 
                and curr_tile_det["arena"] == i_det["arena"]): 
              if i_det["sector"] != "": 
                if i_det["sector"] not in s_mem[world]: 
                  s_mem[world][i_det["sector"]] = dict()
              if i_det["arena"] != "": 
                if i_det["arena"] not in s_mem[world][i_det["sector"]]: 
                  s_mem[world][i_det["sector"]][i_det["arena"]] = list()
              if i_det["game_object"] != "": 
                if (i_det["game_object"] 
                    not in s_mem[world][i_det["sector"]][i_det["arena"]]):
                  s_mem[world][i_det["sector"]][i_det["arena"]] += [
                                                         i_det["game_object"]]

        # Incrementally outputting the s_mem and saving the json file. 
        print ("= " * 15)
        out_file = fs_temp_storage + "/path_tester_out.json"
        with open(out_file, "w") as outfile: 
          outfile.write(json.dumps(s_mem, indent=2))
        print_tree(s_mem)

      except:
        pass

      time.sleep(self.server_sleep * 10)


  def start_server(self, int_counter): 
    """
    The main backend server of Reverie. 
    This function retrieves the environment file from the frontend to 
    understand the state of the world, calls on each personas to make 
    decisions based on the world state, and saves their moves at certain step
    intervals. 
    INPUT
      int_counter: Integer value for the number of steps left for us to take
                   in this iteration. 
    OUTPUT 
      None
    """
    # <sim_folder> points to the current simulation folder.
    sim_folder = f"{fs_storage}/{self.sim_code}"

    # When a persona arrives at a game object, we give a unique event
    # to that object. 
    # e.g., ('double studio[...]:bed', 'is', 'unmade', 'unmade')
    # Later on, before this cycle ends, we need to return that to its 
    # initial state, like this: 
    # e.g., ('double studio[...]:bed', None, None, None)
    # So we need to keep track of which event we added. 
    # <game_obj_cleanup> is used for that. 
    game_obj_cleanup = dict()

    # The main while loop of Reverie. 
    while (True): 
      # Done with this iteration if <int_counter> reaches 0. 
      if int_counter == 0: 
        break

      # <curr_env_file> file is the file that our frontend outputs. When the
      # frontend has done its job and moved the personas, then it will put a 
      # new environment file that matches our step count. That's when we run 
      # the content of this for loop. Otherwise, we just wait. 
      curr_env_file = f"{sim_folder}/environment/{self.step}.json"
      if check_if_file_exists(curr_env_file):
        if debug:
          print(f"[DEBUG] Found environment file for step {self.step}: {curr_env_file}")
        # If we have an environment file, it means we have a new perception
        # input to our personas. So we first retrieve it.
        try: 
          # Try and save block for robustness of the while loop.
          with open(curr_env_file) as json_file:
            new_env = json.load(json_file)
            env_retrieved = True
        except: 
          pass
      
        if env_retrieved: 
          # This is where we go through <game_obj_cleanup> to clean up all 
          # object actions that were used in this cylce. 
          for key, val in game_obj_cleanup.items(): 
            # We turn all object actions to their blank form (with None). 
            self.maze.turn_event_from_tile_idle(key, val)
          # Then we initialize game_obj_cleanup for this cycle. 
          game_obj_cleanup = dict()

          # We first move our personas in the backend environment to match 
          # the frontend environment. In some edge cases, the current
          # environment JSON may be missing a persona key (e.g., if the
          # frontend did not write that agent for this frame). To avoid
          # crashing the whole simulation with a KeyError, we skip any
          # persona that does not appear in new_env for this step.
          for persona_name, persona in self.personas.items(): 
            # 专家即使不在前端环境文件中也需要执行move()以生成行为
            experts_and_moderator = [
              "Public Health Expert",
              "Market Supervision Expert", 
              "Education Bureau Representative",
              "Meeting Moderator"
            ]
            
            if persona_name not in new_env and persona_name not in experts_and_moderator:
              continue
            # <curr_tile> is the tile that the persona was at previously. 
            curr_tile = self.personas_tile[persona_name]
            
            # 如果专家不在new_env中，保持当前位置不变，但仍然执行move()
            if persona_name in new_env:
              # <new_tile> is the tile that the persona will move to right now,
              # during this cycle. 
              new_tile = (new_env[persona_name]["x"], 
                          new_env[persona_name]["y"])

              # We actually move the persona on the backend tile map here. 
              self.personas_tile[persona_name] = new_tile
              self.maze.remove_subject_events_from_tile(persona.name, curr_tile)
              self.maze.add_event_from_tile(persona.scratch
                                           .get_curr_event_and_desc(), new_tile)
            else:
              # 专家不在前端环境中，保持当前位置
              new_tile = curr_tile

            # Now, the persona will travel to get to their destination. *Once*
            # the persona gets there, we activate the object action.
            if not persona.scratch.planned_path: 
              # We add that new object action event to the backend tile map. 
              # At its creation, it is stored in the persona's backend. 
              game_obj_cleanup[persona.scratch
                               .get_curr_obj_event_and_desc()] = new_tile
              self.maze.add_event_from_tile(persona.scratch
                                     .get_curr_obj_event_and_desc(), new_tile)
              # We also need to remove the temporary blank action for the 
              # object that is currently taking the action. 
              blank = (persona.scratch.get_curr_obj_event_and_desc()[0], 
                       None, None, None)
              self.maze.remove_event_from_tile(blank, new_tile)

          # Then we need to actually have each of the personas perceive and
          # move. The movement for each of the personas comes in the form of
          # x y coordinates where the persona will move towards. e.g., (50, 34)
          # This is where the core brains of the personas are invoked. 
          movements = {"persona": dict(), 
                       "meta": dict()}
          for persona_name, persona in self.personas.items(): 
            # <next_tile> is a x,y coordinate. e.g., (58, 9)
            # <pronunciatio> is an emoji. e.g., "\ud83d\udca4"
            # <description> is a string description of the movement. e.g., 
            #   writing her next novel (editing her novel) 
            #   @ double studio:double studio:common room:sofa
            next_tile, pronunciatio, description = persona.move(
              self.maze, self.personas, self.personas_tile[persona_name], 
              self.curr_time)

            # ========== 专家23:00强制移动到会议地点 ==========
            # 停下一切工作（对话、睡觉等），使用寻路系统移动到目标位置！
            experts_and_moderator = [
              "Public Health Expert",
              "Market Supervision Expert", 
              "Education Bureau Representative",
              "Meeting Moderator"
            ]
            # 每个专家分配不同的目标坐标（2x2区域，避免冲突）
            EXPERT_MEETING_TARGETS = {
              "Public Health Expert": (139, 49),
              "Market Supervision Expert": (139, 50),
              "Education Bureau Representative": (138, 49),
              "Meeting Moderator": (138, 50)
            }
            
            if persona_name in experts_and_moderator and self.curr_time.hour >= 23:
              curr_pos = self.personas_tile[persona_name]
              target = EXPERT_MEETING_TARGETS[persona_name]
              
              # 判断是否已到达目标（允许1格容差）
              at_target = (abs(curr_pos[0] - target[0]) <= 1 and 
                          abs(curr_pos[1] - target[1]) <= 1)
              
              # 检查是否已有指向目标的有效路径（避免每步重算）
              # 情况1：planned_path 仍有元素且终点是目标
              # 情况2：next_tile 已经是目标（路径刚好走完）
              has_valid_path = ((persona.scratch.planned_path and 
                                len(persona.scratch.planned_path) > 0 and
                                persona.scratch.planned_path[-1] == target) or
                               next_tile == target)
              
              # 如果还没到达目标位置，使用寻路系统强制移动
              if not at_target:
                # 强制停止对话！同时清空聊天对象的状态
                if persona.scratch.chatting_with:
                  chat_partner_name = persona.scratch.chatting_with
                  if chat_partner_name in self.personas:
                    partner = self.personas[chat_partner_name]
                    partner.scratch.chat = None
                    partner.scratch.chatting_with = None
                    partner.scratch.chatting_end_time = None
                    print(f"🔇 清空聊天对象 {chat_partner_name} 的对话状态")
                
                persona.scratch.chat = None
                persona.scratch.chatting_with = None
                persona.scratch.chatting_end_time = None
                
                # 只在没有有效路径时才重新计算（优化性能）
                if not has_valid_path:
                  # 使用path_finder计算路径（考虑障碍物）
                  try:
                    path = path_finder(self.maze.collision_maze, curr_pos, target, collision_block_id)
                    
                    if path and len(path) > 1:
                      # 设置寻路路径
                      persona.scratch.planned_path = path[1:]
                      persona.scratch.act_path_set = True  # 防止下一步被覆盖！
                      next_tile = path[1]
                      print(f"🚨 强制寻路: {persona_name} 从 {curr_pos} 到 {target}，路径长度 {len(path)}")
                    else:
                      # 寻路失败，使用简单直线移动作为备用
                      dx = 1 if target[0] > curr_pos[0] else (-1 if target[0] < curr_pos[0] else 0)
                      dy = 1 if target[1] > curr_pos[1] else (-1 if target[1] < curr_pos[1] else 0)
                      next_tile = (curr_pos[0] + dx, curr_pos[1] + dy)
                      print(f"⚠️ 寻路失败，直线移动: {persona_name} {curr_pos} -> {next_tile}")
                  except Exception as e:
                    # 异常时使用简单移动
                    dx = 1 if target[0] > curr_pos[0] else (-1 if target[0] < curr_pos[0] else 0)
                    dy = 1 if target[1] > curr_pos[1] else (-1 if target[1] < curr_pos[1] else 0)
                    next_tile = (curr_pos[0] + dx, curr_pos[1] + dy)
                    print(f"⚠️ 寻路异常({e})，直线移动: {persona_name}")
                else:
                  # 已有有效路径，execute()已经取出了下一步，不需要再取
                  # next_tile 已经由 persona.move() 返回，这里只需确保状态正确
                  persona.scratch.act_path_set = True
                  print(f"🚶 使用现有路径: {persona_name} -> {next_tile}")
                
                pronunciatio = "🚨"
                description = f"URGENT: walking to expert meeting at {target}"
              else:
                # 已到达目标，标记为已到达
                if EXPERT_MONITOR_AVAILABLE and self.expert_monitor:
                  if persona_name not in self.expert_monitor.experts_arrived:
                    self.expert_monitor.experts_arrived.add(persona_name)
                    print(f"✅ {persona_name} 已到达会议地点 {curr_pos}")
            # ========== 专家强制移动结束 ==========
            
            # 检查专家是否已到达目标位置并应该隐藏
            should_hide_expert = False
            if (persona_name in experts_and_moderator and 
                EXPERT_MONITOR_AVAILABLE and self.expert_monitor and 
                hasattr(self.expert_monitor, 'experts_arrived')):
              should_hide_expert = persona_name in self.expert_monitor.experts_arrived
            
            # 只有到达目标位置的专家才隐藏
            if not should_hide_expert:
              movements["persona"][persona_name] = {}
              movements["persona"][persona_name]["movement"] = next_tile
              movements["persona"][persona_name]["pronunciatio"] = pronunciatio
              movements["persona"][persona_name]["description"] = description
              movements["persona"][persona_name]["chat"] = (persona
                                                            .scratch.chat)

          # Include the meta information about the current stage in the 
          # movements dictionary. 
          movements["meta"]["curr_time"] = (self.curr_time 
                                             .strftime("%B %d, %Y, %H:%M:%S"))

          # We then write the personas' movements to a file that will be sent 
          # to the frontend server. 
          # Example json output: 
          # {"persona": {"Maria Lopez": {"movement": [58, 9]}},
          #  "persona": {"Klaus Mueller": {"movement": [38, 12]}}, 
          #  "meta": {curr_time: <datetime>}}
          curr_move_file = f"{sim_folder}/movement/{self.step}.json"
          try:
            with open(curr_move_file, "w") as outfile: 
              outfile.write(json.dumps(movements, indent=2))
            if debug:
              print(f"[DEBUG] Wrote movement file: {curr_move_file}")
          except Exception as e:
            print(f"[ERROR] Failed to write movement file {curr_move_file}: {e}")

          # After this cycle, the world takes one step forward, and the 
          # current time moves by <sec_per_step> amount. 
          self.step += 1
          self.curr_time += datetime.timedelta(seconds=self.sec_per_step)

          # 每 50 步自动保存一次记忆（无 LLM 调用，纯文件写入）
          if self.step % 50 == 0:
            try:
              self.save()
              print(f"[AutoSave] 第 {self.step} 步，记忆已保存")
            except Exception as e:
              print(f"[AutoSave] 保存失败: {e}")

          # 在 22:55 触发一次：收集民意并写入专家记忆
          try:
            if self.curr_time.hour == 22 and self.curr_time.minute >= 55:
              curr_date = self.curr_time.date()
              if not hasattr(self, 'last_opinion_collection_date') or self.last_opinion_collection_date != curr_date:
                print(f"\n[Reverie] 触发会议前民意收集 @ {self.curr_time}")
                collect_and_inject_opinions(self.personas, self.curr_time)
                self.last_opinion_collection_date = curr_date
          except Exception as e:
            print(f"[Reverie] 民意收集异常: {e}")
            pass

          # 在每天 23:00 触发一次：从平民聊天中汇总舆论，并写入专家长期记忆。
          try:
            if self.curr_time.hour == 23:
              curr_date = self.curr_time.date()
              if self.last_public_opinion_date != curr_date:
                generate_and_broadcast_public_opinion(
                  self.personas,
                  self.curr_time,
                )
                self.last_public_opinion_date = curr_date
                
              # 23:00后开始检查专家位置（无需启动监控）
              if EXPERT_MONITOR_AVAILABLE and self.expert_monitor:
                self.expert_monitor_started = True
                
          except Exception:
            # 不让舆论模块的异常影响主循环
            pass
          
          # 06:00 重置专家状态（会议结束，新的一天开始）
          if self.curr_time.hour == 6 and self.curr_time.minute == 0:
            if EXPERT_MONITOR_AVAILABLE and self.expert_monitor:
              if self.expert_monitor.experts_arrived or self.expert_monitor.trigger_sent:
                print(f"[Reverie] 06:00 重置专家会议状态")
                self.expert_monitor.experts_arrived = set()
                self.expert_monitor.trigger_sent = False
                self.expert_monitor_started = False
          
          # 检查专家位置监控触发
          try:
            if (EXPERT_MONITOR_AVAILABLE and self.expert_monitor and 
                self.expert_monitor_started and not self.expert_monitor.trigger_sent):
              # 直接从内存中的位置数据获取专家位置
              for expert_name in ["Education Bureau Representative", "Meeting Moderator", 
                                "Public Health Expert", "Market Supervision Expert"]:
                expert_pos = self.personas_tile.get(expert_name)
                
                # 检查是否到达目标位置（传入expert_name检查各自的目标）
                if self.expert_monitor.is_at_target_position(expert_pos, expert_name):
                  if expert_name not in self.expert_monitor.experts_arrived:
                    self.expert_monitor.experts_arrived.add(expert_name)
                    print(f"[Monitor] ✓ {expert_name} 已到达目标位置 {expert_pos}")
              
              # 检查是否所有专家都到达
              if len(self.expert_monitor.experts_arrived) == 4:
                self.expert_monitor.trigger_expert_meeting()
                
          except Exception as e:
            print(f"[Reverie] 专家位置监控异常: {e}")
            pass

          int_counter -= 1
          
      # Sleep so we don't burn our machines. 
      time.sleep(self.server_sleep)


  def open_server(self): 
    """
    Open up an interactive terminal prompt that lets you run the simulation 
    step by step and probe agent state. 

    INPUT 
      None
    OUTPUT
      None
    """
    print ("Note: The agents in this simulation package are computational")
    print ("constructs powered by generative agents architecture and LLM. We")
    print ("clarify that these agents lack human-like agency, consciousness,")
    print ("and independent decision-making.\n---")

    # <sim_folder> points to the current simulation folder.
    sim_folder = f"{fs_storage}/{self.sim_code}"

    while True: 
      sim_command = input("Enter option: ")
      sim_command = sim_command.strip()
      ret_str = ""

      try: 
        if sim_command.lower() in ["f", "fin", "finish", "save and finish"]: 
          # Finishes the simulation environment and saves the progress. 
          # Example: fin
          self.save()
          break

        elif sim_command.lower() == "start path tester mode": 
          # Starts the path tester and removes the currently forked sim files.
          # Note that once you start this mode, you need to exit out of the
          # session and restart in case you want to run something else. 
          shutil.rmtree(sim_folder) 
          self.start_path_tester_server()

        elif sim_command.lower() == "exit": 
          # Finishes the simulation environment but does not save the progress
          # and erases all saved data from current simulation. 
          # Example: exit 
          shutil.rmtree(sim_folder) 
          break 

        elif sim_command.lower() == "save": 
          # Saves the current simulation progress. 
          # Example: save
          self.save()

        elif sim_command[:3].lower() == "run": 
          # Runs the number of steps specified in the prompt.
          # Example: run 1000
          int_count = int(sim_command.split()[-1])
          rs.start_server(int_count)

        elif ("print persona schedule" 
              in sim_command[:22].lower()): 
          # Print the decomposed schedule of the persona specified in the 
          # prompt.
          # Example: print persona schedule Isabella Rodriguez
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.get_str_daily_schedule_summary())

        elif ("print all persona schedule" 
              in sim_command[:26].lower()): 
          # Print the decomposed schedule of all personas in the world. 
          # Example: print all persona schedule
          for persona_name, persona in self.personas.items(): 
            ret_str += f"{persona_name}\n"
            ret_str += f"{persona.scratch.get_str_daily_schedule_summary()}\n"
            ret_str += f"---\n"

        elif ("print hourly org persona schedule" 
              in sim_command.lower()): 
          # Print the hourly schedule of the persona specified in the prompt.
          # This one shows the original, non-decomposed version of the 
          # schedule.
          # Ex: print persona schedule Isabella Rodriguez
          ret_str += (self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.get_str_daily_schedule_hourly_org_summary())

        elif ("print persona current tile" 
              in sim_command[:26].lower()): 
          # Print the x y tile coordinate of the persona specified in the 
          # prompt. 
          # Ex: print persona current tile Isabella Rodriguez
          ret_str += str(self.personas[" ".join(sim_command.split()[-2:])]
                      .scratch.curr_tile)

        elif ("print persona chatting with buffer" 
              in sim_command.lower()): 
          # Print the chatting with buffer of the persona specified in the 
          # prompt.
          # Ex: print persona chatting with buffer Isabella Rodriguez
          curr_persona = self.personas[" ".join(sim_command.split()[-2:])]
          for p_n, count in curr_persona.scratch.chatting_with_buffer.items(): 
            ret_str += f"{p_n}: {count}"

        elif ("print persona associative memory (event)" 
              in sim_command.lower()):
          # Print the associative memory (event) of the persona specified in
          # the prompt
          # Ex: print persona associative memory (event) Isabella Rodriguez
          prefix = "print persona associative memory (event)"
          persona_name = sim_command[len(prefix):].strip()
          ret_str += f'{self.personas[persona_name]}\n'
          ret_str += self.personas[persona_name].a_mem.get_str_seq_events()

        elif ("print persona associative memory (thought)" 
              in sim_command.lower()): 
          # Print the associative memory (thought) of the persona specified in
          # the prompt
          # Ex: print persona associative memory (thought) Isabella Rodriguez
          prefix = "print persona associative memory (thought)"
          persona_name = sim_command[len(prefix):].strip()
          ret_str += f'{self.personas[persona_name]}\n'
          ret_str += self.personas[persona_name].a_mem.get_str_seq_thoughts()

        elif ("print persona associative memory (chat)" 
              in sim_command.lower()): 
          # Print the associative memory (chat) of the persona specified in
          # the prompt
          # Ex: print persona associative memory (chat) Isabella Rodriguez
          prefix = "print persona associative memory (chat)"
          persona_name = sim_command[len(prefix):].strip()
          ret_str += f'{self.personas[persona_name]}\n'
          ret_str += self.personas[persona_name].a_mem.get_str_seq_chats()

        elif ("print persona spatial memory" 
              in sim_command.lower()): 
          # Print the spatial memory of the persona specified in the prompt
          # Ex: print persona spatial memory Isabella Rodriguez
          self.personas[" ".join(sim_command.split()[-2:])].s_mem.print_tree()

        elif ("print current time" 
              in sim_command[:18].lower()): 
          # Print the current time of the world. 
          # Ex: print current time
          ret_str += f'{self.curr_time.strftime("%B %d, %Y, %H:%M:%S")}\n'
          ret_str += f'steps: {self.step}'

        elif ("print tile event" 
              in sim_command[:16].lower()): 
          # Print the tile events in the tile specified in the prompt 
          # Ex: print tile event 50, 30
          cooordinate = [int(i.strip()) for i in sim_command[16:].split(",")]
          for i in self.maze.access_tile(cooordinate)["events"]: 
            ret_str += f"{i}\n"

        elif ("print tile details" 
              in sim_command.lower()): 
          # Print the tile details of the tile specified in the prompt 
          # Ex: print tile event 50, 30
          cooordinate = [int(i.strip()) for i in sim_command[18:].split(",")]
          for key, val in self.maze.access_tile(cooordinate).items(): 
            ret_str += f"{key}: {val}\n"

        elif ("call -- analysis" 
              in sim_command.lower()): 
          # Starts a stateless chat session with the agent. It does not save 
          # anything to the agent's memory. 
          # Ex: call -- analysis Isabella Rodriguez
          persona_name = sim_command[len("call -- analysis"):].strip() 
          self.personas[persona_name].open_convo_session("analysis")

        elif ("call -- load history" 
              in sim_command.lower()): 
          curr_file = maze_assets_loc + "/" + sim_command[len("call -- load history"):].strip() 
          # call -- load history the_ville/agent_history_init_n3.csv

          rows = read_file_to_list(curr_file, header=True, strip_trail=True)[1]
          clean_whispers = []
          for row in rows: 
            agent_name = row[0].strip() 
            whispers = row[1].split(";")
            whispers = [whisper.strip() for whisper in whispers]
            for whisper in whispers: 
              clean_whispers += [[agent_name, whisper]]

          load_history_via_whisper(self.personas, clean_whispers)

        print (ret_str)

      except:
        traceback.print_exc()
        print ("Error.")
        pass


if __name__ == '__main__':
  # rs = ReverieServer("base_the_ville_isabella_maria_klaus", 
  #                    "July1_the_ville_isabella_maria_klaus-step-3-1")
  # rs = ReverieServer("July1_the_ville_isabella_maria_klaus-step-3-20", 
  #                    "July1_the_ville_isabella_maria_klaus-step-3-21")
  # rs.open_server()

  origin = input("Enter the name of the forked simulation: ").strip()
  target = input("Enter the name of the new simulation: ").strip()

  rs = ReverieServer(origin, target)
  rs.open_server()




















































