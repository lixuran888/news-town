import os, json, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sims = [d for d in os.listdir(storage) if d.startswith('auto_run')]
sims.sort(reverse=True)
sim_dir = os.path.join(storage, sims[0])
print(f'模拟: {sims[0]}')
print('=' * 80)

personas_dir = os.path.join(sim_dir, 'personas')
seen_chats = set()  # 避免重复显示同一对话
all_chats = []  # 收集所有对话

# 先收集所有对话
for persona_name in os.listdir(personas_dir):
    nodes_path = os.path.join(personas_dir, persona_name, 'bootstrap_memory', 'associative_memory', 'nodes.json')
    if not os.path.exists(nodes_path):
        continue
    
    with open(nodes_path, encoding='utf-8') as f:
        nodes = json.load(f)
    
    if not isinstance(nodes, dict):
        continue
    
    for node_id, node in nodes.items():
        if node.get('type') == 'chat':
            filling = node.get('filling', [])
            # 用前两条发言作为唯一标识，避免重复
            chat_key = str(filling[:2]) if filling else node.get('description', '')
            if chat_key in seen_chats:
                continue
            seen_chats.add(chat_key)
            all_chats.append(node)

# 按时间排序
def parse_time(t):
    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
    except:
        return datetime.min

all_chats.sort(key=lambda x: parse_time(x.get('created', '')))

# 显示排序后的对话
for i, node in enumerate(all_chats, 1):
    print(f'\n{"=" * 80}')
    print(f'对话 {i}')
    print(f'时间: {node.get("created")}')
    print(f'描述: {node.get("description")}')
    print(f'参与者: {node.get("subject")} & {node.get("object")}')
    print('-' * 80)
    
    for j, line in enumerate(node.get('filling', []), 1):
        speaker = line[0]
        text = line[1]
        print(f'\n[{j}] {speaker}:')
        print(f'    {text}')
    
    print()

print('=' * 80)
print(f'\n共 {len(all_chats)} 组独立对话')
