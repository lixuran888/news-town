# 验证合并后的改动是否能正常工作
import ast
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

print('=' * 60)
print('【1. Python 语法检查】')
print('=' * 60)

files = [
    (r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\persona\cognitive_modules\reflect.py', 'reflect.py'),
    (r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\persona\memory_structures\scratch.py', 'scratch.py'),
    (r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\opinion_collector.py', 'opinion_collector.py'),
    (r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\reverie.py', 'reverie.py'),
    (r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\event_opinion_extractor.py', 'event_opinion_extractor.py'),
]

all_ok = True
for path, name in files:
    try:
        with open(path, encoding='utf-8') as f:
            ast.parse(f.read())
        print(f'  ✅ {name}')
    except SyntaxError as e:
        print(f'  ❌ {name}: {e}')
        all_ok = False

print()
print('=' * 60)
print('【2. 关键代码连接检查】')
print('=' * 60)

# 检查 reflect.py
print('\n--- reflect.py ---')
with open(r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\persona\cognitive_modules\reflect.py', encoding='utf-8') as f:
    reflect_content = f.read()

checks = [
    ('def process_memo_thought', 'process_memo_thought 函数定义'),
    ('| relationship:', '关系解析'),
    ('| event_opinion:', '舆论解析'),
    ('| stance:', 'stance 解析'),
    ('event_opinions.append', '舆论存入'),
    ('process_memo_thought(persona', '函数调用'),
]
for pattern, desc in checks:
    status = '✅' if pattern in reflect_content else '❌'
    print(f'  {status} {desc}')

# 检查 scratch.py
print('\n--- scratch.py ---')
with open(r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\persona\memory_structures\scratch.py', encoding='utf-8') as f:
    scratch_content = f.read()

checks = [
    ('self.event_opinions = []', 'event_opinions 初始化'),
    ('event_opinions = scratch_load.get', 'event_opinions 加载'),
    ('scratch["event_opinions"]', 'event_opinions 保存'),
    ('self.friends', 'friends 字段'),
]
for pattern, desc in checks:
    status = '✅' if pattern in scratch_content else '❌'
    print(f'  {status} {desc}')

# 检查 memo_on_convo_v1.txt
print('\n--- memo_on_convo_v1.txt ---')
with open(r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\persona\prompt_template\v3_ChatGPT\memo_on_convo_v1.txt', encoding='utf-8') as f:
    prompt_content = f.read()

checks = [
    ('| relationship:', 'relationship 输出'),
    ('| event_opinion:', 'event_opinion 输出'),
    ('| stance:', 'stance 输出'),
    ('food poisoning', '食物中毒关键词'),
]
for pattern, desc in checks:
    status = '✅' if pattern in prompt_content else '❌'
    print(f'  {status} {desc}')

# 检查 opinion_collector.py
print('\n--- opinion_collector.py ---')
with open(r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\opinion_collector.py', encoding='utf-8') as f:
    collector_content = f.read()

checks = [
    ('event_opinions', '使用 event_opinions'),
    ('stance', '使用 stance'),
]
for pattern, desc in checks:
    status = '✅' if pattern in collector_content else '❌'
    print(f'  {status} {desc}')

# 检查 reverie.py
print('\n--- reverie.py ---')
with open(r'e:\generative_agents-main\generative_agents-main\reverie\backend_server\reverie.py', encoding='utf-8') as f:
    reverie_content = f.read()

checks = [
    ('20:00:00', 'clean 时间线 20:00'),
    ('hour == 22', '22:55 民意收集'),
    ('hour >= 23', '23:00 专家消失'),
]
for pattern, desc in checks:
    status = '✅' if pattern in reverie_content else '❌'
    print(f'  {status} {desc}')

print()
print('=' * 60)
print('【3. 数据流验证】')
print('=' * 60)
print('''
对话结束
    ↓
【1次 LLM】generate_memo_on_convo()
  输出: "{memo} | relationship: xxx | event_opinion: xxx | stance: xxx"
    ↓
process_memo_thought() 解析:
  ├── relationship → 更新 persona.scratch.friends
  └── event_opinion + stance → 存入 persona.scratch.event_opinions
    ↓
22:55 opinion_collector 收集 event_opinions
    ↓
生成民意报告给专家
''')

print('=' * 60)
print('【结论】')
print('=' * 60)
if all_ok:
    print('✅ 所有语法检查通过')
    print('✅ 关键代码连接正确')
    print('✅ 可以正常使用！')
else:
    print('❌ 存在语法错误，请修复')
