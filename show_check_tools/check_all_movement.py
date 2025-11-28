import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sims = sorted([d for d in os.listdir(storage) if d.startswith('auto_run')], reverse=True)
sim_dir = os.path.join(storage, sims[0])
movement_dir = os.path.join(sim_dir, 'movement')

# 获取最近 30 个 movement 文件
files = sorted([f for f in os.listdir(movement_dir) if f.endswith('.json')], 
               key=lambda x: int(x.split('.')[0]), reverse=True)[:30]

print(f'模拟: {sims[0]}')
print(f'分析最近 30 步的移动情况')
print('=' * 80)

# 收集所有角色的位置历史
all_positions = {}

for f in files:
    with open(os.path.join(movement_dir, f), encoding='utf-8') as fp:
        data = json.load(fp)
    
    for name, info in data.get('persona', {}).items():
        if name not in all_positions:
            all_positions[name] = {'positions': [], 'actions': [], 'icons': []}
        pos = tuple(info.get('movement', [0,0]))
        all_positions[name]['positions'].append(pos)
        all_positions[name]['actions'].append(info.get('description', '')[:40])
        all_positions[name]['icons'].append(info.get('pronunciatio', ''))

# 分析每个角色
print('\n移动状态分析:')
print('-' * 80)

moving_agents = []
stationary_agents = []

for name, data in sorted(all_positions.items()):
    positions = data['positions']
    unique_pos = len(set(positions))
    latest_icon = data['icons'][0] if data['icons'] else ''
    latest_action = data['actions'][0] if data['actions'] else ''
    
    # 判断是否在移动
    is_moving = unique_pos > 5
    
    # 检查是否是"应该静止但在移动"的情况
    static_keywords = ['sleeping', 'reading', 'working', 'sitting', 'eating']
    should_be_static = any(kw in latest_action.lower() for kw in static_keywords)
    
    status = ''
    if is_moving and should_be_static:
        status = '⚠️ 异常(应静止但在动)'
    elif is_moving:
        status = '🚶 移动中'
    else:
        status = '✅ 静止'
    
    print(f'{name}:')
    print(f'  30步位置变化: {unique_pos} 个不同位置  {status}')
    print(f'  图标: {latest_icon}  动作: {latest_action}')
    print()
    
    if is_moving:
        moving_agents.append((name, unique_pos, latest_action))

print('=' * 80)
print(f'移动中的角色: {len(moving_agents)}')
for name, pos_count, action in moving_agents:
    print(f'  {name}: {pos_count}个位置, {action}')
