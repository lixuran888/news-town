#!/usr/bin/env python3
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

# 检查最新simulation的状态
sim_dir = r'e:\generative_agents-main\environment\frontend_server\storage\auto_run_20251129_232526'

print('=== 当前Simulation状态 ===')

# 1. 检查当前时间
try:
    with open(os.path.join(sim_dir, 'reverie', 'meta.json'), 'r', encoding='utf-8') as f:
        meta = json.load(f)
    print(f"当前时间: {meta.get('curr_time')}")
    print(f"当前步数: {meta.get('step')}")
except Exception as e:
    print(f"读取meta.json失败: {e}")

# 2. 检查最新的movement文件
movement_dir = os.path.join(sim_dir, 'movement')
if os.path.exists(movement_dir):
    movement_files = [f for f in os.listdir(movement_dir) if f.endswith('.json')]
    if movement_files:
        # 找到最新的movement文件
        latest_step = max([int(f.split('.')[0]) for f in movement_files])
        latest_file = os.path.join(movement_dir, f'{latest_step}.json')
        
        print(f"\n最新movement文件: {latest_step}.json")
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                movement_data = json.load(f)
            
            # 检查专家位置
            experts = [
                "Education Bureau Representative",
                "Meeting Moderator", 
                "Public Health Expert",
                "Market Supervision Expert"
            ]
            
            print(f"模拟时间: {movement_data.get('meta', {}).get('curr_time')}")
            print("\n专家位置:")
            for expert in experts:
                if expert in movement_data.get('persona', {}):
                    pos = movement_data['persona'][expert].get('movement', [0,0])
                    desc = movement_data['persona'][expert].get('description', '')[:50]
                    print(f"  {expert}: {pos} - {desc}")
                else:
                    print(f"  {expert}: 未找到")
                    
        except Exception as e:
            print(f"读取movement文件失败: {e}")
    else:
        print("没有找到movement文件")
else:
    print("movement目录不存在")

# 3. 计算时间差
try:
    from datetime import datetime
    if 'meta' in locals():
        curr_time_str = meta.get('curr_time')
        if curr_time_str:
            curr_time = datetime.strptime(curr_time_str, "%B %d, %Y, %H:%M:%S")
            target_time = curr_time.replace(hour=23, minute=0, second=0)
            
            if curr_time < target_time:
                diff = target_time - curr_time
                print(f"\n距离23:00还有: {diff}")
            else:
                print(f"\n已过23:00: {curr_time.strftime('%H:%M:%S')}")
except Exception as e:
    print(f"时间计算失败: {e}")
