#!/usr/bin/env python3
import os, json, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

print('📅 检查最新时间线所有人的日程安排')
print('=' * 100)

# 1. 找到最新的simulation
storage_path = r'e:\generative_agents-main\environment\frontend_server\storage'
auto_runs = [d for d in os.listdir(storage_path) if d.startswith('auto_run_')]
if not auto_runs:
    print("❌ 没有找到auto_run目录")
    exit(1)

latest_sim = max(auto_runs)
sim_dir = os.path.join(storage_path, latest_sim)
print(f"🎯 最新simulation: {latest_sim}")

# 2. 检查meta.json获取所有persona
try:
    meta_file = os.path.join(sim_dir, 'reverie', 'meta.json')
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    curr_time = meta.get('curr_time', 'Unknown')
    step = meta.get('step', 0)
    persona_names = meta.get('persona_names', [])
    
    print(f"⏰ 当前时间: {curr_time}")
    print(f"📊 当前步数: {step}")
    print(f"👥 总人数: {len(persona_names)}")
    
except Exception as e:
    print(f"❌ 读取meta.json失败: {e}")
    exit(1)

# 3. 检查每个persona的日程
print(f"\n{'='*100}")
print("📋 所有人的日程安排详情:")
print('='*100)

experts = ["Education Bureau Representative", "Meeting Moderator", "Public Health Expert", "Market Supervision Expert"]

for i, persona_name in enumerate(persona_names, 1):
    print(f"\n【{i}. {persona_name}】")
    print("-" * 80)
    
    # 检查persona目录是否存在
    persona_dir = os.path.join(sim_dir, 'personas', persona_name)
    if not os.path.exists(persona_dir):
        print("❌ persona目录不存在")
        continue
    
    # 读取scratch.json
    scratch_file = os.path.join(persona_dir, 'bootstrap_memory', 'scratch.json')
    if not os.path.exists(scratch_file):
        print("❌ scratch.json不存在")
        continue
    
    try:
        with open(scratch_file, 'r', encoding='utf-8') as f:
            scratch = json.load(f)
        
        # 基本信息
        is_expert = persona_name in experts
        print(f"🏷️  类型: {'🎓 专家' if is_expert else '👤 普通居民'}")
        
        # daily_plan_req
        daily_plan_req = scratch.get('daily_plan_req')
        if daily_plan_req:
            print(f"📝 Daily Plan Req:")
            # 检查是否包含23:00任务
            has_23_task = '23:00' in daily_plan_req or '11:00pm' in daily_plan_req
            if has_23_task and is_expert:
                print(f"   ✅ 包含23:00会议任务")
            elif is_expert:
                print(f"   ❌ 缺少23:00会议任务")
            
            # 显示daily_plan_req内容（截断显示）
            if len(daily_plan_req) > 200:
                print(f"   {daily_plan_req[:200]}...")
            else:
                print(f"   {daily_plan_req}")
        else:
            print(f"📝 Daily Plan Req: ❌ 无")
        
        # f_daily_schedule
        f_daily_schedule = scratch.get('f_daily_schedule', [])
        if f_daily_schedule:
            print(f"⏰ 当前Daily Schedule ({len(f_daily_schedule)}项):")
            
            # 显示前5项和后5项
            show_items = []
            if len(f_daily_schedule) <= 10:
                show_items = f_daily_schedule
            else:
                show_items = f_daily_schedule[:5] + [["...", "..."]] + f_daily_schedule[-5:]
            
            for j, (activity, duration) in enumerate(show_items):
                if activity == "...":
                    print(f"     ... (省略{len(f_daily_schedule)-10}项) ...")
                else:
                    # 计算时间
                    total_minutes = sum([item[1] for item in f_daily_schedule[:j] if item[1] != "..."])
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    print(f"     {hours:02d}:{minutes:02d} - {activity} ({duration}分钟)")
            
            # 检查是否有23:00相关任务
            has_meeting_task = any('meeting' in str(item[0]).lower() or 'coordinates' in str(item[0]) 
                                 for item in f_daily_schedule if len(item) > 0)
            if is_expert:
                if has_meeting_task:
                    print(f"   ✅ Schedule中包含会议相关任务")
                else:
                    print(f"   ❌ Schedule中缺少会议相关任务")
        else:
            print(f"⏰ 当前Daily Schedule: ❌ 无")
        
        # 当前行动
        act_description = scratch.get('act_description')
        if act_description:
            print(f"🎯 当前行动: {act_description}")
        
        # 当前位置
        act_address = scratch.get('act_address')
        if act_address:
            print(f"📍 当前位置: {act_address}")
            
    except Exception as e:
        print(f"❌ 读取{persona_name}的数据失败: {e}")

# 4. 总结
print(f"\n{'='*100}")
print("📊 总结分析:")
print('='*100)

expert_count = len([name for name in persona_names if name in experts])
civilian_count = len(persona_names) - expert_count

print(f"👥 总人数: {len(persona_names)} (专家: {expert_count}, 普通居民: {civilian_count})")
print(f"⏰ 当前时间: {curr_time}")

# 检查时间是否过了23:00
try:
    if curr_time and curr_time != 'Unknown':
        time_obj = datetime.strptime(curr_time, "%B %d, %Y, %H:%M:%S")
        if time_obj.hour >= 23:
            print(f"🕚 已过23:00 - 专家应该开始移动")
        else:
            remaining = (23 - time_obj.hour) * 60 - time_obj.minute
            print(f"⏳ 距离23:00还有约{remaining}分钟")
except:
    print(f"❓ 时间格式无法解析")

print(f"\n🎯 重点关注:")
print(f"   • 专家是否保留了daily_plan_req中的23:00任务")
print(f"   • 专家的f_daily_schedule是否基于新的daily_plan_req生成")
print(f"   • 普通居民的daily_plan_req是否被正确清空并重新生成")
