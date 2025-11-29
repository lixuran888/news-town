import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sims = sorted([d for d in os.listdir(storage) if d.startswith('auto_run')], reverse=True)
sim_dir = os.path.join(storage, sims[0])
movement_dir = os.path.join(sim_dir, 'movement')

# 获取最新步数
files = sorted([f for f in os.listdir(movement_dir) if f.endswith('.json')], key=lambda x: int(x.split('.')[0]), reverse=True)
latest = files[0]
with open(os.path.join(movement_dir, latest), encoding='utf-8') as f:
    data = json.load(f)

print(f'模拟: {sims[0]}')
print(f'步数: {latest.split(".")[0]}')
print(f'时间: {data["meta"]["curr_time"]}')
print()

# 检查角色位置
positions = {}
for name, info in data.get('persona', {}).items():
    pos = tuple(info.get('movement', [0,0]))
    if pos not in positions:
        positions[pos] = []
    positions[pos].append(name)

print('=== 同位置角色 ===')
found_same = False
for pos, names in positions.items():
    if len(names) > 1:
        print(f'{pos}: {names}')
        found_same = True
if not found_same:
    print('(无)')

print()
print('=== 近距离角色 (<5格) ===')
all_p = list(data.get('persona', {}).items())
found_close = False
for i in range(len(all_p)):
    for j in range(i+1, len(all_p)):
        n1, i1 = all_p[i]
        n2, i2 = all_p[j]
        p1, p2 = i1.get('movement',[0,0]), i2.get('movement',[0,0])
        d = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
        if d < 5:
            print(f'{n1} <-> {n2}: {d:.1f}格')
            found_close = True
if not found_close:
    print('(无)')

print()
print('=== 所有角色位置 ===')
for name, info in sorted(data.get('persona', {}).items()):
    pos = info.get('movement', [0,0])
    desc = info.get('description', '')[:40]
    print(f'{name}: {pos} - {desc}')

print()
print('=' * 80)

# 检查每个角色的对话冷却状态
personas_dir = os.path.join(sim_dir, 'personas')

print('\n=== 对话冷却状态 (chatting_with_buffer) ===')
for name in sorted(os.listdir(personas_dir)):
    scratch_path = os.path.join(personas_dir, name, 'bootstrap_memory', 'scratch.json')
    if os.path.exists(scratch_path):
        with open(scratch_path, encoding='utf-8') as f:
            s = json.load(f)
        buffer = s.get('chatting_with_buffer', {})
        chatting = s.get('chatting_with')
        act_desc = s.get('act_description', '')[:40]
        
        if buffer or chatting:
            print(f'\n{name}:')
            print(f'  正在对话: {chatting}')
            print(f'  冷却中: {buffer}')
            print(f'  动作: {act_desc}')

# 检查最近的 movement 文件中的对话状态
print('\n\n=== 最近步数中的对话状态 ===')
movement_dir = os.path.join(sim_dir, 'movement')
files = sorted([f for f in os.listdir(movement_dir) if f.endswith('.json')],
               key=lambda x: int(x.split('.')[0]), reverse=True)

# 检查最近 100 步有没有对话
chat_steps = []
for f in files[:500]:
    with open(os.path.join(movement_dir, f), encoding='utf-8') as fp:
        data = json.load(fp)
    
    step = int(f.split('.')[0])
    for name, info in data.get('persona', {}).items():
        if info.get('chat'):
            chat_steps.append((step, name, data['meta']['curr_time']))

if chat_steps:
    print(f'最近 500 步中有 {len(chat_steps)} 次对话状态:')
    for step, name, time in chat_steps[:10]:
        print(f'  步 {step}: {name} @ {time}')
else:
    print('最近 500 步没有任何对话状态！')

# 检查角色位置分布
print('\n\n=== 当前角色位置 ===')
latest_file = files[0]
with open(os.path.join(movement_dir, latest_file), encoding='utf-8') as f:
    data = json.load(f)

positions = {}
for name, info in data.get('persona', {}).items():
    pos = tuple(info.get('movement', [0,0]))
    if pos not in positions:
        positions[pos] = []
    positions[pos].append(name)

print(f'时间: {data["meta"]["curr_time"]}')
print(f'\n同位置的角色:')
for pos, names in positions.items():
    if len(names) > 1:
        print(f'  {pos}: {names}')

# 计算角色间距离
print('\n角色间距离（< 10格）:')
all_personas = list(data.get('persona', {}).items())
for i in range(len(all_personas)):
    for j in range(i+1, len(all_personas)):
        n1, info1 = all_personas[i]
        n2, info2 = all_personas[j]
        p1 = info1.get('movement', [0,0])
        p2 = info2.get('movement', [0,0])
        dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5
        if dist < 10:
            print(f'  {n1} <-> {n2}: {dist:.1f} 格')
