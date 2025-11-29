# 检查对话何时结束 + scratch 数据
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'
# 自动获取最新的模拟
sims = sorted([d for d in os.listdir(storage) if d.startswith('auto_run')], reverse=True)
sim = sims[0] if sims else None
print(f'检查模拟: {sim}')

# 检查 scratch 数据
print('=' * 60)
print('【检查 scratch 中的 chatting_end_time】')
print('=' * 60)

personas = ['Education Bureau Representative', 'Ayesha Khan', 'Meeting Moderator', 'Klaus Mueller']

for persona in personas:
    scratch_path = os.path.join(storage, sim, 'personas', persona, 'bootstrap_memory', 'scratch.json')
    if os.path.exists(scratch_path):
        with open(scratch_path, encoding='utf-8') as f:
            data = json.load(f)
        print(f'\n{persona}:')
        print(f'  chatting_with: {data.get("chatting_with")}')
        print(f'  chatting_end_time: {data.get("chatting_end_time")}')
        print(f'  chat轮数: {len(data.get("chat", []) or [])}')

print()
print('=' * 60)
print('【检查 movement 中的对话结束时间点】')
print('=' * 60)

movement_dir = os.path.join(storage, sim, 'movement')
files = sorted([f for f in os.listdir(movement_dir) if f.endswith('.json')], 
               key=lambda x: int(x.split('.')[0]))

print(f'总步数: {len(files)}')

# 追踪每个角色的对话状态变化
for persona in personas:
    print(f'\n--- {persona} ---')
    prev_has_chat = None
    chat_start = None
    
    for f in files:
        step = int(f.split('.')[0])
        with open(os.path.join(movement_dir, f), encoding='utf-8') as fp:
            data = json.load(fp)
        
        info = data.get('persona', {}).get(persona, {})
        chat = info.get('chat')
        has_chat = chat is not None and len(chat) > 0
        desc = info.get('description', '')[:40]
        time_str = data.get('meta', {}).get('curr_time', '')
        
        if prev_has_chat is not None and has_chat != prev_has_chat:
            if has_chat:
                print(f'  Step {step}: 开始对话 @ {time_str}')
                chat_start = step
            else:
                duration = step - chat_start if chat_start else 0
                print(f'  Step {step}: 对话结束 @ {time_str} (持续 {duration} 步)')
        
        prev_has_chat = has_chat
    
    if prev_has_chat:
        print(f'  ⚠️ 最后一步仍在对话中！')
