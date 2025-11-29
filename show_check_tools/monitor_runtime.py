# 运行时监控脚本
# 功能：
#   1. 查看当前运行步数
#   2. 检测 DeepSeek API 错误
#   3. 检测降级 (fallback/downgrade)
#   4. 追踪 prompt 调用情况

import os
import json
import sys
import re
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================
STORAGE_PATH = r'e:\generative_agents-main\environment\frontend_server\storage'

# Prompt 用途说明
PROMPT_DESCRIPTIONS = {
    # === 日程规划相关 ===
    'wake_up_hour': '🌅 判断起床时间',
    'daily_plan': '📋 生成每日计划',
    'daily_planning': '📋 每日计划生成',
    'generate_hourly_schedule': '⏰ 生成每小时日程',
    'task_decomp': '📝 任务分解',
    'decide_to_talk': '🗣️ 决定是否交谈',
    'decide_to_react': '⚡ 决定是否反应',
    
    # === 对话相关 ===
    'create_conversation': '💬 生成对话内容',
    'summarize_conversation': '📝 总结对话',
    'memo_on_convo': '💭 对话后备忘录+关系+舆论',
    'agent_chat': '💬 Agent 对话',
    'utterance': '🎤 生成发言',
    
    # === 记忆与反思 ===
    'generate_focal_pt': '🎯 生成关注焦点',
    'generate_insights': '💡 生成洞察',
    'generate_poig_score': '⭐ 计算重要性分数',
    'planning_thought_on_convo': '🧠 对话后规划想法',
    'action_event_triple': '🔗 生成事件三元组',
    
    # === 行动执行 ===
    'action_location': '📍 决定行动位置',
    'action_game_object': '🎮 选择游戏对象',
    'action_pronunciatio': '😊 生成表情/动作符号',
    'new_decomp_schedule': '📅 新分解日程',
    
    # === 其他 ===
    'run_gpt_prompt': '🤖 通用 GPT 调用',
    'safe_generate': '🛡️ 安全生成响应',
    'extract_event_opinion': '📊 提取事件舆论',
}

def get_latest_sim():
    """获取最新的模拟目录"""
    sims = sorted([d for d in os.listdir(STORAGE_PATH) 
                   if d.startswith('auto_run')], reverse=True)
    return sims[0] if sims else None

def get_current_step():
    """获取当前运行步数"""
    sim = get_latest_sim()
    if not sim:
        return None, None
    
    meta_path = os.path.join(STORAGE_PATH, sim, 'reverie', 'meta.json')
    movement_dir = os.path.join(STORAGE_PATH, sim, 'movement')
    
    step = 0
    curr_time = "unknown"
    
    if os.path.exists(meta_path):
        with open(meta_path, encoding='utf-8') as f:
            meta = json.load(f)
        step = meta.get('step', 0)
        curr_time = meta.get('curr_time', 'unknown')
    
    # 也可以从 movement 目录判断
    if os.path.exists(movement_dir):
        files = [f for f in os.listdir(movement_dir) if f.endswith('.json')]
        step = max(step, len(files))
    
    return step, curr_time, sim

def analyze_log_file(log_path):
    """分析日志文件（如果有的话）"""
    errors = []
    downgrades = []
    prompt_calls = defaultdict(int)
    
    if not os.path.exists(log_path):
        return errors, downgrades, prompt_calls
    
    with open(log_path, encoding='utf-8', errors='ignore') as f:
        for line in f:
            # 检测 API 错误
            if 'DeepSeek API ERROR' in line:
                errors.append(line.strip())
            if 'TOKEN LIMIT EXCEEDED' in line:
                errors.append(line.strip())
            
            # 检测降级
            if 'downgrade' in line.lower() or 'fail_safe' in line.lower():
                downgrades.append(line.strip())
            if '[LLM FILTER]' in line:
                downgrades.append(line.strip())
            
            # 检测 prompt 调用
            for key in PROMPT_DESCRIPTIONS.keys():
                if key in line.lower():
                    prompt_calls[key] += 1
    
    return errors, downgrades, prompt_calls

def check_persona_status(sim):
    """检查每个角色的当前状态"""
    personas_dir = os.path.join(STORAGE_PATH, sim, 'personas')
    status = {}
    
    if not os.path.exists(personas_dir):
        return status
    
    for persona_name in os.listdir(personas_dir):
        scratch_path = os.path.join(personas_dir, persona_name, 'bootstrap_memory', 'scratch.json')
        if os.path.exists(scratch_path):
            with open(scratch_path, encoding='utf-8') as f:
                data = json.load(f)
            status[persona_name] = {
                'currently': data.get('currently', '')[:50],
                'chatting_with': data.get('chatting_with'),
                'chatting_end_time': data.get('chatting_end_time'),
                'event_opinions': len(data.get('event_opinions', []) or []),
            }
    
    return status

def print_report():
    """打印完整报告"""
    print('=' * 70)
    print('🖥️  运行时监控报告')
    print('=' * 70)
    print(f'⏰ 报告时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # 1. 当前步数
    print('─' * 70)
    print('【1. 当前运行状态】')
    print('─' * 70)
    step, curr_time, sim = get_current_step()
    if sim:
        print(f'  📁 模拟目录: {sim}')
        print(f'  🔢 当前步数: {step}')
        print(f'  🕐 模拟时间: {curr_time}')
    else:
        print('  ❌ 未找到运行中的模拟')
        return
    
    # 2. 角色状态
    print()
    print('─' * 70)
    print('【2. 角色状态】')
    print('─' * 70)
    personas = check_persona_status(sim)
    for name, info in personas.items():
        chat_status = f"💬 与 {info['chatting_with']} 对话中" if info['chatting_with'] else "🟢 空闲"
        opinions = f"📊 {info['event_opinions']}条舆论" if info['event_opinions'] else ""
        print(f'  {name}:')
        print(f'    状态: {chat_status} {opinions}')
        print(f'    正在: {info["currently"]}...')
    
    # 3. 检查日志（如果有）
    log_patterns = [
        os.path.join(STORAGE_PATH, sim, 'log.txt'),
        os.path.join(STORAGE_PATH, '..', '..', 'reverie.log'),
    ]
    
    errors_found = []
    downgrades_found = []
    
    for log_path in log_patterns:
        if os.path.exists(log_path):
            errors, downgrades, _ = analyze_log_file(log_path)
            errors_found.extend(errors)
            downgrades_found.extend(downgrades)
    
    # 4. API 错误
    print()
    print('─' * 70)
    print('【3. DeepSeek API 状态】')
    print('─' * 70)
    if errors_found:
        print(f'  ❌ 发现 {len(errors_found)} 个 API 错误:')
        for err in errors_found[-5:]:  # 只显示最近5个
            print(f'    • {err[:80]}...')
    else:
        print('  ✅ 未检测到 API 错误')
    
    # 5. 降级情况
    print()
    print('─' * 70)
    print('【4. 降级情况】')
    print('─' * 70)
    if downgrades_found:
        print(f'  ⚠️ 发现 {len(downgrades_found)} 次降级:')
        for dg in downgrades_found[-5:]:
            print(f'    • {dg[:80]}...')
    else:
        print('  ✅ 未检测到降级')
    
    # 6. Prompt 用途说明
    print()
    print('─' * 70)
    print('【5. Prompt 调用说明】')
    print('─' * 70)
    print('  以下是主要 Prompt 的用途:')
    for key, desc in list(PROMPT_DESCRIPTIONS.items())[:15]:
        print(f'    • {key}: {desc}')
    print('  ...')
    
    print()
    print('=' * 70)
    print('💡 提示: 运行模拟时终端会显示实时日志，观察以下关键词:')
    print('   • "DeepSeek API ERROR" - API 调用失败')
    print('   • "TOKEN LIMIT EXCEEDED" - Token 超限')
    print('   • "[LLM FILTER] downgrade" - 触发降级')
    print('   • "[Chat End]" - 对话正常结束')
    print('   • "[EventOpinion]" - 舆论提取成功')
    print('   • "[Friends]" - 关系更新成功')
    print('=' * 70)

def check_chat_detail():
    """检查对话详细信息"""
    sim = get_latest_sim()
    if not sim:
        print("未找到模拟")
        return
    
    print('=' * 70)
    print('🔍 对话详细检查')
    print('=' * 70)
    
    # 检查 scratch 中的对话状态
    personas_dir = os.path.join(STORAGE_PATH, sim, 'personas')
    for persona_name in os.listdir(personas_dir):
        scratch_path = os.path.join(personas_dir, persona_name, 'bootstrap_memory', 'scratch.json')
        if os.path.exists(scratch_path):
            with open(scratch_path, encoding='utf-8') as f:
                data = json.load(f)
            if data.get('chatting_with') or data.get('chat'):
                print(f'\n{persona_name}:')
                print(f'  chatting_with: {data.get("chatting_with")}')
                print(f'  chatting_end_time: {data.get("chatting_end_time")}')
                chat = data.get('chat')
                print(f'  chat: {len(chat) if chat else 0} 轮')
    
    # 检查最新 movement 文件
    movement_dir = os.path.join(STORAGE_PATH, sim, 'movement')
    files = sorted([f for f in os.listdir(movement_dir) if f.endswith('.json')], 
                   key=lambda x: int(x.split('.')[0]))
    latest = files[-1]
    
    print(f'\n最新 movement 文件: {latest}')
    with open(os.path.join(movement_dir, latest), encoding='utf-8') as f:
        data = json.load(f)
    
    has_chat = False
    for name, info in data.get('persona', {}).items():
        chat = info.get('chat')
        if chat:
            has_chat = True
            print(f'  {name}: {len(chat)} 轮对话')
    
    if not has_chat:
        print('  ⚠️ movement 文件中没有 chat 数据')

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'chat':
        check_chat_detail()
    else:
        print_report()
