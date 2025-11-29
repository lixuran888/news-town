# 检查对话状态问题
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sim = 'auto_run_20251129_143226'
movement_dir = os.path.join(storage, sim, 'movement')

# 统计每一步的对话情况
chat_stats = {}
total_chats = 0

files = sorted([f for f in os.listdir(movement_dir) if f.endswith('.json')], 
               key=lambda x: int(x.split('.')[0]))

print(f'总步数: {len(files)}')
print()

# 分析每一步
for f in files[:50]:  # 只看前50步
    step = int(f.split('.')[0])
    with open(os.path.join(movement_dir, f), encoding='utf-8') as fp:
        data = json.load(fp)
    
    chatting_personas = []
    for name, info in data.get('persona', {}).items():
        chat = info.get('chat')
        if chat:  # 如果有 chat 数据
            chatting_personas.append(name)
            total_chats += 1
    
    if chatting_personas:
        print(f'Step {step}: {len(chatting_personas)} 人在对话 - {chatting_personas[:3]}...')

print()
print(f'前50步中总对话状态数: {total_chats}')
print()

# 检查第一步的详细数据
print('=' * 60)
print('【Step 0 详细数据】')
print('=' * 60)
with open(os.path.join(movement_dir, '0.json'), encoding='utf-8') as f:
    data = json.load(f)

for name, info in data.get('persona', {}).items():
    chat = info.get('chat')
    desc = info.get('description', '')[:50]
    print(f'{name}:')
    print(f'  description: {desc}')
    print(f'  chat: {chat}')
    print()
