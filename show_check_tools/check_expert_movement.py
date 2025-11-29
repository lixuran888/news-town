import os, json, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

# 检查专家位置和移动情况
storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sims = [d for d in os.listdir(storage) if d.startswith('auto_run')]
sims.sort(reverse=True)
sim_dir = os.path.join(storage, sims[0])
print(f'检查模拟: {sims[0]}')
print('=' * 80)

# 专家名单
experts = [
    "Education Bureau Representative",
    "Meeting Moderator", 
    "Public Health Expert",
    "Market Supervision Expert"
]

# 目标位置
TARGET_X, TARGET_Y = 145, 50

# 检查movement文件
movement_dir = os.path.join(sim_dir, 'movement')
if os.path.exists(movement_dir):
    movement_files = [f for f in os.listdir(movement_dir) if f.endswith('.json')]
    movement_files.sort(key=lambda x: int(x.split('.')[0]))
    
    print(f"找到 {len(movement_files)} 个movement文件")
    
    # 检查最新几个movement文件
    for filename in movement_files[-5:]:
        filepath = os.path.join(movement_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        step = filename.split('.')[0]
        print(f"\n=== Step {step} ===")
        
        if 'persona' in data:
            for expert_name in experts:
                if expert_name in data['persona']:
                    movement = data['persona'][expert_name]['movement']
                    x, y = movement
                    distance = ((x - TARGET_X)**2 + (y - TARGET_Y)**2)**0.5
                    print(f"{expert_name}: ({x}, {y}) -> 距离目标: {distance:.1f}")
                else:
                    print(f"{expert_name}: 未找到位置数据")
        
        # 检查当前时间
        if 'meta' in data and 'curr_time' in data['meta']:
            print(f"当前时间: {data['meta']['curr_time']}")

else:
    print("未找到movement目录")

# 检查专家的daily_plan
print(f"\n{'='*80}")
print("检查专家的daily_plan:")

personas_dir = os.path.join(sim_dir, 'personas')
for expert_name in experts:
    expert_dir = os.path.join(personas_dir, expert_name)
    if os.path.exists(expert_dir):
        scratch_file = os.path.join(expert_dir, 'bootstrap_memory', 'scratch.json')
        if os.path.exists(scratch_file):
            with open(scratch_file, 'r', encoding='utf-8') as f:
                scratch = json.load(f)
            
            print(f"\n--- {expert_name} ---")
            if 'daily_plan_req' in scratch:
                print(f"Daily Plan: {scratch['daily_plan_req']}")
            if 'f_daily_schedule' in scratch:
                schedule = scratch['f_daily_schedule']
                print("Schedule:")
                for time_slot, activity in schedule:
                    print(f"  {time_slot}: {activity}")
        else:
            print(f"{expert_name}: 未找到scratch.json")
    else:
        print(f"{expert_name}: 专家目录不存在")
