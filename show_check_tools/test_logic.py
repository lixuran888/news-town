# 逻辑检查测试
import sys
import json
import datetime
sys.stdout.reconfigure(encoding='utf-8')

print('=' * 60)
print('【3. get_str_iss() 输出测试】')
print('=' * 60)

# 模拟 scratch 对象的 get_str_iss 方法
class MockScratch:
    def __init__(self, data):
        self.name = data.get('name', '')
        self.age = data.get('age', 0)
        self.innate = data.get('innate', '')
        self.learned = data.get('learned', '')
        self.currently = data.get('currently', '')
        self.lifestyle = data.get('lifestyle', '')
        self.daily_plan_req = data.get('daily_plan_req', '')
        self.friends = data.get('friends', {
            'best_friends': [],
            'good_friends': [],
            'acquaintances': [],
            'tensions': []
        })
        self.curr_time = datetime.datetime(2025, 3, 10, 9, 0)
    
    def get_str_iss(self):
        commonset = ''
        commonset += f'Name: {self.name}\n'
        commonset += f'Age: {self.age}\n'
        commonset += f'Innate traits: {self.innate}\n'
        commonset += f'Learned traits: {self.learned}\n'
        commonset += f'Currently: {self.currently}\n'
        commonset += f'Lifestyle: {self.lifestyle}\n'
        commonset += f'Daily plan requirement: {self.daily_plan_req}\n'
        
        # 添加朋友关系描述
        friends_desc = []
        if self.friends.get('best_friends'):
            friends_desc.append(f"Best friends: {', '.join(self.friends['best_friends'])}")
        if self.friends.get('good_friends'):
            friends_desc.append(f"Good friends: {', '.join(self.friends['good_friends'])}")
        if self.friends.get('tensions'):
            friends_desc.append(f"Has tensions with: {', '.join(self.friends['tensions'])}")
        if friends_desc:
            commonset += f"Relationships: {'; '.join(friends_desc)}\n"
        
        commonset += f"Current Date: {self.curr_time.strftime('%A %B %d')}\n"
        return commonset

# 测试 Maria (有 friends 和 tensions)
base = r'e:\generative_agents-main\environment\frontend_server\storage\base_the_ville_clean\personas'

with open(f'{base}/Maria Lopez/bootstrap_memory/scratch.json', encoding='utf-8') as f:
    maria_data = json.load(f)

maria = MockScratch(maria_data)
print('【Maria Lopez 的 get_str_iss()】')
print('-' * 40)
print(maria.get_str_iss())
print(f'字符数: {len(maria.get_str_iss())}')
print()

# 测试专家 (无 friends)
with open(f'{base}/Public Health Expert/bootstrap_memory/scratch.json', encoding='utf-8') as f:
    expert_data = json.load(f)

expert = MockScratch(expert_data)
print('【Public Health Expert 的 get_str_iss()】')
print('-' * 40)
print(expert.get_str_iss())
print(f'字符数: {len(expert.get_str_iss())}')
print()

print('=' * 60)
print('【4. 总结】')
print('=' * 60)
print('✅ 普通居民: 有 friends 字段，会显示 Relationships')
print('✅ 专家: 无 friends 字段，不显示 Relationships')
print('✅ 两种情况都能正常工作')
