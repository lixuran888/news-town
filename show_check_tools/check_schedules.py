# 检查日程对比
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

base = r'e:\generative_agents-main\environment\frontend_server\storage\base_the_ville_clean\personas'

names = ['Education Bureau Representative', 'Ayesha Khan', 'Meeting Moderator', 'Klaus Mueller']

print('=' * 70)
print('【日程对比分析 - 为什么总是这几对人对话？】')
print('=' * 70)

for name in names:
    with open(f'{base}/{name}/bootstrap_memory/scratch.json', encoding='utf-8') as f:
        data = json.load(f)
    print(f'\n【{name}】')
    print(f'  daily_plan_req:')
    print(f'    {data.get("daily_plan_req", "N/A")}')
    print(f'  living_area: {data.get("living_area", "N/A")}')

print('\n' + '=' * 70)
print('【问题分析】')
print('=' * 70)
