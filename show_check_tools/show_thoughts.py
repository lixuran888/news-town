import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sims = sorted([d for d in os.listdir(storage) if d.startswith('auto_run')], reverse=True)
sim_dir = os.path.join(storage, sims[0])
personas_dir = os.path.join(sim_dir, 'personas')

print(f'模拟: {sims[0]}')
print('=' * 80)

# 收集所有反思
all_thoughts = []

for name in os.listdir(personas_dir):
    nodes_path = os.path.join(personas_dir, name, 'bootstrap_memory', 'associative_memory', 'nodes.json')
    if not os.path.exists(nodes_path):
        continue
    
    with open(nodes_path, encoding='utf-8') as f:
        nodes = json.load(f)
    
    if not isinstance(nodes, dict):
        continue
    
    for node_id, node in nodes.items():
        if node.get('type') == 'thought':
            all_thoughts.append({
                'persona': name,
                'time': node.get('created'),
                'description': node.get('description', ''),
                'poignancy': node.get('poignancy', 0)
            })

# 按时间排序
all_thoughts.sort(key=lambda x: x['time'])

# 显示前20条和最后10条
print(f'\n总反思数: {len(all_thoughts)}')
print('\n' + '=' * 80)
print('最早的 10 条反思:')
print('=' * 80)

for i, t in enumerate(all_thoughts[:10], 1):
    print(f'\n[{i}] {t["persona"]} @ {t["time"]} (重要性: {t["poignancy"]})')
    print(f'    {t["description"][:150]}')

print('\n' + '=' * 80)
print('最新的 10 条反思:')
print('=' * 80)

for i, t in enumerate(all_thoughts[-10:], len(all_thoughts)-9):
    print(f'\n[{i}] {t["persona"]} @ {t["time"]} (重要性: {t["poignancy"]})')
    print(f'    {t["description"][:150]}')

# 分析活跃度
print('\n' + '=' * 80)
print('活跃度分析:')
print('=' * 80)

# 统计每个角色
from collections import Counter
persona_counts = Counter(t['persona'] for t in all_thoughts)
print('\n按反思数排序:')
for name, count in persona_counts.most_common():
    print(f'  {name}: {count} 条')

# 统计高重要性反思
high_poignancy = [t for t in all_thoughts if t['poignancy'] >= 7]
print(f'\n高重要性反思 (>=7): {len(high_poignancy)} 条')
for t in high_poignancy[:5]:
    print(f'  [{t["poignancy"]}] {t["persona"]}: {t["description"][:80]}...')
