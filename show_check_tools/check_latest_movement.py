#!/usr/bin/env python3
import os, json, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

# 检查最新simulation的专家位置
storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sim_dir = os.path.join(storage, 'auto_run_20251129_215113')
print(f'检查模拟: auto_run_20251129_215113')
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

# 检查最新的movement文件
movement_dir = os.path.join(sim_dir, 'movement')
if os.path.exists(movement_dir):
    movement_files = [f for f in os.listdir(movement_dir) if f.endswith('.json')]
    movement_files.sort(key=lambda x: int(x.split('.')[0]))
    
    print(f"找到 {len(movement_files)} 个movement文件")
    
    # 检查最新几个movement文件
    for filename in movement_files[-5:]:
        filepath = os.path.join(movement_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            step = filename.split('.')[0]
            print(f"\n=== Step {step} ===")
            
            if 'persona' in data:
                for expert_name in experts:
                    if expert_name in data['persona']:
                        movement_data = data['persona'][expert_name]
                        if 'movement' in movement_data:
                            movement = movement_data['movement']
                            x, y = movement
                            distance = ((x - TARGET_X)**2 + (y - TARGET_Y)**2)**0.5
                            print(f"{expert_name}: ({x}, {y}) -> 距离目标: {distance:.1f}")
                        else:
                            print(f"{expert_name}: 无movement数据")
                    else:
                        print(f"{expert_name}: 未找到位置数据")
            
            # 检查当前时间
            if 'meta' in data and 'curr_time' in data['meta']:
                print(f"当前时间: {data['meta']['curr_time']}")
                
        except Exception as e:
            print(f"读取 {filename} 失败: {e}")

else:
    print("未找到movement目录")

print(f"\n{'='*80}")
print("检查专家的personas目录:")

personas_dir = os.path.join(sim_dir, 'personas')
if os.path.exists(personas_dir):
    for expert_name in experts:
        expert_dir = os.path.join(personas_dir, expert_name)
        if os.path.exists(expert_dir):
            print(f"{expert_name}: 目录存在")
            items = os.listdir(expert_dir)
            print(f"  内容: {items}")
        else:
            print(f"{expert_name}: 目录不存在")
else:
    print("personas目录不存在")
