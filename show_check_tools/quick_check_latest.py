#!/usr/bin/env python3
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage_path = r'e:\generative_agents-main\environment\frontend_server\storage'
auto_runs = [d for d in os.listdir(storage_path) if d.startswith('auto_run_')]
if auto_runs:
    latest = max(auto_runs)
    print(f"🎯 最新simulation: {latest}")
    
    # 检查meta.json
    meta_path = os.path.join(storage_path, latest, 'reverie', 'meta.json')
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        print(f"⏰ 当前时间: {meta.get('curr_time')}")
        print(f"📊 步数: {meta.get('step')}")
        print(f"🔗 Fork from: {meta.get('fork_sim_code')}")
        
        # 检查专家的daily_plan_req
        experts = ["Education Bureau Representative", "Meeting Moderator", "Public Health Expert", "Market Supervision Expert"]
        
        print(f"\n🎓 专家daily_plan_req检查:")
        for expert in experts:
            scratch_path = os.path.join(storage_path, latest, 'personas', expert, 'bootstrap_memory', 'scratch.json')
            if os.path.exists(scratch_path):
                with open(scratch_path, 'r', encoding='utf-8') as f:
                    scratch = json.load(f)
                daily_plan_req = scratch.get('daily_plan_req')
                if daily_plan_req:
                    has_23_task = '23:00' in daily_plan_req or '11:00pm' in daily_plan_req
                    print(f"  ✅ {expert}: {'包含23:00任务' if has_23_task else '无23:00任务'}")
                else:
                    print(f"  ❌ {expert}: daily_plan_req = None")
            else:
                print(f"  ❓ {expert}: 文件不存在")
    else:
        print("❌ meta.json不存在")
else:
    print("❌ 没有auto_run目录")
