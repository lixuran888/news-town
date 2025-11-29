#!/usr/bin/env python3
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

# 检查专家当前状态
sim_dir = r'e:\generative_agents-main\environment\frontend_server\storage\auto_run_20251129_215113'
print('检查专家当前状态')
print('=' * 80)

experts = [
    "Education Bureau Representative",
    "Meeting Moderator", 
    "Public Health Expert",
    "Market Supervision Expert"
]

# 1. 检查专家的scratch.json（如果存在）
personas_dir = os.path.join(sim_dir, 'personas')
for expert_name in experts:
    expert_dir = os.path.join(personas_dir, expert_name)
    print(f"\n--- {expert_name} ---")
    
    if os.path.exists(expert_dir):
        scratch_file = os.path.join(expert_dir, 'bootstrap_memory', 'scratch.json')
        if os.path.exists(scratch_file):
            try:
                with open(scratch_file, 'r', encoding='utf-8') as f:
                    scratch = json.load(f)
                
                print(f"Daily Plan Req: {scratch.get('daily_plan_req', 'None')}")
                
                if 'f_daily_schedule' in scratch and scratch['f_daily_schedule']:
                    print("Current Schedule:")
                    for time_slot, activity in scratch['f_daily_schedule'][-5:]:  # 最后5个
                        print(f"  {time_slot}: {activity}")
                else:
                    print("No schedule found")
                    
            except Exception as e:
                print(f"读取scratch.json失败: {e}")
        else:
            print("scratch.json不存在")
    else:
        print("专家目录不存在")

# 2. 检查base_the_ville_clean中的配置
print(f"\n{'='*80}")
print("检查base_the_ville_clean中的daily_plan_req:")

base_dir = r'e:\generative_agents-main\environment\frontend_server\storage\base_the_ville_clean'
for expert_name in experts:
    expert_dir = os.path.join(base_dir, 'personas', expert_name)
    scratch_file = os.path.join(expert_dir, 'bootstrap_memory', 'scratch.json')
    
    print(f"\n--- {expert_name} (base) ---")
    if os.path.exists(scratch_file):
        try:
            with open(scratch_file, 'r', encoding='utf-8') as f:
                scratch = json.load(f)
            
            daily_plan = scratch.get('daily_plan_req', 'None')
            if '(145, 50)' in daily_plan:
                print("✓ 包含目标位置 (145, 50)")
            else:
                print("✗ 不包含目标位置")
            print(f"Daily Plan: {daily_plan}")
            
        except Exception as e:
            print(f"读取失败: {e}")
    else:
        print("文件不存在")
