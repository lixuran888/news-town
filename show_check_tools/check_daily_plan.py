# 检查角色日程设定
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage\base_the_ville_clean\personas'

print('=' * 70)
print('角色日程设定 (daily_plan_req)')
print('=' * 70)

# 分类显示
experts = ['Education Bureau Representative', 'Meeting Moderator', 'Public Health Expert', 'Market Supervision Expert']
students = ['Ayesha Khan', 'Klaus Mueller', 'Maria Lopez']
others = ['Abigail Chen', 'Adam Smith', 'Arthur Burton', 'Carlos Gomez', 'Carmen Ortiz', 'Isabella Rodriguez']

def show_persona(name):
    scratch_path = os.path.join(storage, name, 'bootstrap_memory', 'scratch.json')
    if os.path.exists(scratch_path):
        with open(scratch_path, encoding='utf-8') as f:
            data = json.load(f)
        daily = data.get('daily_plan_req', '')
        print(f'\n【{name}】')
        print(f'  {daily[:200]}...' if len(daily) > 200 else f'  {daily}')

print('\n--- 专家角色 ---')
for p in experts:
    show_persona(p)

print('\n--- 学生角色 ---')
for p in students:
    show_persona(p)

print('\n--- 其他居民 ---')
for p in others:
    show_persona(p)
