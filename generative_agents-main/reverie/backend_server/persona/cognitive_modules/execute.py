"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: execute.py
Description: This defines the "Act" module for generative agents. 
"""
import sys
import random
sys.path.append('../../')

from global_methods import *
from path_finder import *
from utils import *

def execute(persona, maze, personas, plan): 
  """
  Given a plan (action's string address), we execute the plan (actually 
  outputs the tile coordinate path and the next coordinate for the 
  persona). 

  INPUT:
    persona: Current <Persona> instance.  
    maze: An instance of current <Maze>.
    personas: A dictionary of all personas in the world. 
    plan: This is a string address of the action we need to execute. 
       It comes in the form of "{world}:{sector}:{arena}:{game_objects}". 
       It is important that you access this without doing negative 
       indexing (e.g., [-1]) because the latter address elements may not be 
       present in some cases. 
       e.g., "dolores double studio:double studio:bedroom 1:bed"
    
  OUTPUT: 
    execution
  """
  # 若 plan 异常缺失，直接保持原地以避免后续 None 下标错误
  if not isinstance(plan, str) or not plan.strip():
    fallback_tile = persona.scratch.curr_tile or (0, 0)
    persona.scratch.curr_tile = fallback_tile
    return fallback_tile, "...", "idle (invalid plan)"

  # 防御性校验：curr_tile 可能在某些专家/主持人场景下未被写入
  curr_tile = persona.scratch.curr_tile
  if (not isinstance(curr_tile, (list, tuple)) or len(curr_tile) < 2 
      or curr_tile[0] is None or curr_tile[1] is None):
    # 回退到 (0,0)，并写回 scratch，避免 path_finder 处理 None 时报错
    print(f"[execute] WARNING: invalid curr_tile for {persona.name}: {curr_tile}, fallback to (0,0)")
    curr_tile = (0, 0)
    persona.scratch.curr_tile = curr_tile

  if "<random>" in plan and persona.scratch.planned_path == []: 
    persona.scratch.act_path_set = False

  # <act_path_set> is set to True if the path is set for the current action. 
  # It is False otherwise, and means we need to construct a new path. 
  if not persona.scratch.act_path_set: 
    # <target_tiles> is a list of tile coordinates where the persona may go 
    # to execute the current action. The goal is to pick one of them.
    target_tiles = None


    if "<persona>" in plan: 
      # Executing persona-persona interaction.
      target_persona_name_raw = plan.split("<persona>")[-1].strip()
      # 先将中文名转换为拼音（兼容记忆中的中文名）
      from persona.cognitive_modules.plan import normalize_persona_name
      target_persona_name = normalize_persona_name(target_persona_name_raw)
      # 安全检查：确保目标persona存在
      if target_persona_name not in personas:
        print(f"[execute] WARNING: Target persona '{target_persona_name_raw}' (normalized: '{target_persona_name}') not found in personas dict, skipping interaction")
        return persona.scratch.curr_tile, "...", f"idle (target {target_persona_name} not found)"
      target_p_tile = personas[target_persona_name].scratch.curr_tile
      potential_path = path_finder(maze.collision_maze, 
                                   persona.scratch.curr_tile, 
                                   target_p_tile, 
                                   collision_block_id)
      if len(potential_path) <= 2: 
        target_tiles = [potential_path[0]]
      else: 
        potential_1 = path_finder(maze.collision_maze, 
                                persona.scratch.curr_tile, 
                                potential_path[int(len(potential_path)/2)], 
                                collision_block_id)
        potential_2 = path_finder(maze.collision_maze, 
                                persona.scratch.curr_tile, 
                                potential_path[int(len(potential_path)/2)+1], 
                                collision_block_id)
        if len(potential_1) <= len(potential_2): 
          target_tiles = [potential_path[int(len(potential_path)/2)]]
        else: 
          target_tiles = [potential_path[int(len(potential_path)/2+1)]]
    
    elif "<waiting>" in plan: 
      # Executing interaction where the persona has decided to wait before 
      # executing their action.
      x = int(plan.split()[1])
      y = int(plan.split()[2])
      target_tiles = [[x, y]]

    elif "<random>" in plan: 
      # Executing a random location action.
      # plan 形如 "the Ville:Town Hall:kitchen:<random>"；这里先去掉
      # ":<random>" 后缀，然后在该地址下面随机选一个 tile。
      base_addr = ":".join(plan.split(":")[:-1])

      if base_addr in maze.address_tiles:
        target_tiles = maze.address_tiles[base_addr]
        
        # 如果已经在目标区域内，就停留在当前位置，避免无限走动
        curr_tile = tuple(persona.scratch.curr_tile)
        if curr_tile in target_tiles:
          target_tiles = [list(curr_tile)]  # 停在原地
        else:
          target_tiles = random.sample(list(target_tiles), 1)
      else:
        # 与默认分支相同的回退策略，避免 DeepSeek 生成的非法地址导致 KeyError。
        living_addr = None
        try:
          living_addr = persona.scratch.living_area
        except Exception:
          living_addr = None

        if living_addr and living_addr in maze.address_tiles:
          target_tiles = maze.address_tiles[living_addr]
          target_tiles = random.sample(list(target_tiles), 1)
        else:
          target_tiles = [persona.scratch.curr_tile]  # 停在原地

    else: 
      # This is our default execution. We simply take the persona to the
      # location where the current action is taking place. 
      # Retrieve the target addresses. Again, plan is an action address in its
      # string form. <maze.address_tiles> takes this and returns candidate 
      # coordinates. 
      if plan not in maze.address_tiles:
        # 有时 DeepSeek 会生成地图中不存在的地址（例如 "the Ville:Town Hall:kitchen"）。
        # 为避免 KeyError 或后续使用 None 触发崩溃，这里做回退策略：
        # 1）优先尝试 persona 的 living_area（例如 "the_ville:Dorm:bedroom"）
        # 2）如果 living_area 也不在 address_tiles，则退回当前 tile，保持原地不动。
        living_addr = None
        try:
          # living_area 形如 "the_ville:Dorm for Oak Hill College:bedroom"
          living_addr = persona.scratch.living_area
        except Exception:
          living_addr = None

        if living_addr and living_addr in maze.address_tiles:
          target_tiles = maze.address_tiles[living_addr]
        else:
          # 退回当前 tile 作为唯一目标点
          target_tiles = [persona.scratch.curr_tile]
      else: 
        target_tiles = maze.address_tiles[plan]

    # There are sometimes more than one tile returned from this (e.g., a tabe
    # may stretch many coordinates). So, we sample a few here. And from that 
    # random sample, we will take the closest ones. 
    if len(target_tiles) < 4: 
      target_tiles = random.sample(list(target_tiles), len(target_tiles))
    else:
      target_tiles = random.sample(list(target_tiles), 4)
    # If possible, we want personas to occupy different tiles when they are 
    # headed to the same location on the maze. It is ok if they end up on the 
    # same time, but we try to lower that probability. 
    # We take care of that overlap here.  
    persona_name_set = set(personas.keys())
    new_target_tiles = []
    for i in target_tiles: 
      curr_event_set = maze.access_tile(i)["events"]
      pass_curr_tile = False
      for j in curr_event_set: 
        if j[0] in persona_name_set: 
          pass_curr_tile = True
      if not pass_curr_tile: 
        new_target_tiles += [i]
    if len(new_target_tiles) == 0: 
      new_target_tiles = target_tiles
    target_tiles = new_target_tiles

    # Now that we've identified the target tile, we find the shortest path to
    # one of the target tiles. 
    curr_tile = persona.scratch.curr_tile
    collision_maze = maze.collision_maze
    closest_target_tile = None
    path = None
    for i in target_tiles: 
      # path_finder takes a collision_mze and the curr_tile coordinate as 
      # an input, and returns a list of coordinate tuples that becomes the
      # path. 
      # e.g., [(0, 1), (1, 1), (1, 2), (1, 3), (1, 4)...]
      curr_path = path_finder(maze.collision_maze, 
                              curr_tile, 
                              i, 
                              collision_block_id)
      if not closest_target_tile: 
        closest_target_tile = i
        path = curr_path
      elif len(curr_path) < len(path): 
        closest_target_tile = i
        path = curr_path

    # Actually setting the <planned_path> and <act_path_set>. We cut the 
    # first element in the planned_path because it includes the curr_tile. 
    persona.scratch.planned_path = path[1:]
    persona.scratch.act_path_set = True
  
  # Setting up the next immediate step. We stay at our curr_tile if there is
  # no <planned_path> left, but otherwise, we go to the next tile in the path.
  ret = persona.scratch.curr_tile
  if persona.scratch.planned_path: 
    ret = persona.scratch.planned_path[0]
    persona.scratch.planned_path = persona.scratch.planned_path[1:]

  description = f"{persona.scratch.act_description}"
  description += f" @ {persona.scratch.act_address}"

  execution = ret, persona.scratch.act_pronunciatio, description
  return execution















