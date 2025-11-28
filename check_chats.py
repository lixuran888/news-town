import json, sys
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# 找最新模拟
storage = Path(r'e:\generative_agents-main\environment\frontend_server\storage')
sims = sorted([p for p in storage.iterdir() if p.is_dir() and p.name.startswith('auto_run')], 
              key=lambda p: p.stat().st_mtime, reverse=True)

if not sims:
    print('No simulation found')
    exit()

sim = sims[0]
print(f'模拟: {sim.name}')

# 检查 movement 文件获取当前时间
movement_dir = sim / 'movement'
if movement_dir.exists():
    files = list(movement_dir.glob('*.json'))
    if files:
        latest = max(files, key=lambda f: int(f.stem))
        with open(latest, encoding='utf-8') as f:
            data = json.load(f)
        print(f'当前步数: {latest.stem}')
        print(f'当前时间: {data.get("meta", {}).get("curr_time", "?")}')
    else:
        print('无 movement 数据')
else:
    print('无 movement 目录')

print()

# 统计所有人的对话
chat_count = defaultdict(int)
total_chats = 0
total_utterances = 0

personas_dir = sim / 'personas'
for p in personas_dir.iterdir():
    if not p.is_dir():
        continue
    nodes_path = p / 'bootstrap_memory' / 'associative_memory' / 'nodes.json'
    if nodes_path.exists():
        with open(nodes_path, encoding='utf-8') as f:
            nodes = json.load(f)
        if isinstance(nodes, dict):
            for n in nodes.values():
                if n.get('type') == 'chat':
                    chat_count[p.name] += 1
                    total_chats += 1
                    filling = n.get('filling', [])
                    total_utterances += len(filling)

print(f'总对话数: {total_chats}')
print(f'总发言条数: {total_utterances}')
print()
if chat_count:
    print('各角色对话数:')
    for name, count in sorted(chat_count.items(), key=lambda x: -x[1]):
        print(f'  {name}: {count}')
else:
    print('(暂无对话)')
