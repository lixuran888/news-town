# 测试 prompt 长度
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 模拟 Adam Smith 的 get_str_iss() 输出
name = 'Adam Smith'
age = 36
innate = 'philosophical, melancholic, introspective, eloquent, cynical, wise'
learned = '''Adam Smith is a middle-aged philosopher who has seen enough of the world to be skeptical about human nature. He writes about creativity but often dwells on life's disappointments. He enjoys intellectual sparring with Carlos at the pub - their debates can get quite heated but they respect each other. Abigail's quiet artistic nature appeals to him. He appreciates Klaus's thoughtful approach to discussions. Isabella's cheerfulness sometimes annoys him but he values her warmth. He speaks in long, thoughtful sentences and often quotes philosophers. 他是个深沉的思考者，常常有悲观的观点，说话慢但有深度。'''
currently = 'Adam Smith is writing a book about the importance of creativity and how it can shape the world.'
lifestyle = 'Adam Smith goes to bed around 8pm, awakes up around 4am, eats dinner around 5pm.'
daily_plan_req = 'Adam Smith wakes up at 4am to write. He goes to Hobbs Cafe mid-morning for breakfast and reading. In the evening he often visits The Rose and Crown Pub for discussions.'
friends = {
    'best_friends': [], 
    'good_friends': ['Carlos Gomez', 'Abigail Chen', 'Klaus Mueller'], 
    'acquaintances': ['Isabella Rodriguez', 'Arthur Burton'], 
    'tensions': []
}

# 构造 commonset (模拟 get_str_iss)
commonset = f"Name: {name}\n"
commonset += f"Age: {age}\n"
commonset += f"Innate traits: {innate}\n"
commonset += f"Learned traits: {learned}\n"
commonset += f"Currently: {currently}\n"
commonset += f"Lifestyle: {lifestyle}\n"
commonset += f"Daily plan requirement: {daily_plan_req}\n"

# 添加朋友关系
friends_desc = []
if friends.get('best_friends'):
    friends_desc.append(f"Best friends: {', '.join(friends['best_friends'])}")
if friends.get('good_friends'):
    friends_desc.append(f"Good friends: {', '.join(friends['good_friends'])}")
if friends.get('tensions'):
    friends_desc.append(f"Has tensions with: {', '.join(friends['tensions'])}")
if friends_desc:
    commonset += f"Relationships: {'; '.join(friends_desc)}\n"

commonset += "Current Date: Saturday March 10\n"

print("=" * 60)
print("【get_str_iss() 输出内容】")
print("=" * 60)
print(commonset)
print("=" * 60)
print(f"字符数: {len(commonset)}")
print(f"占 8000 字符上限的: {len(commonset)/8000*100:.1f}%")
print()

# 模拟完整的 daily_planning prompt
prompt_template = f"""daily_planning_v6.txt

Variables: 
!<INPUT 0>! -- Commonset
!<INPUT 1>! -- Lifestyle
!<INPUT 2>! -- Reverie date time now
!<INPUT 3>! -- Persona first names
!<INPUT 4>! -- wake_up_hour

<commentblockmarker>###</commentblockmarker>
{commonset}

In general, {lifestyle}
Today is Saturday March 10. Here is {name.split()[0]}'s plan today in broad-strokes (with the time of the day. e.g., have a lunch at 12:00 pm, watch TV from 7 to 8 pm): 1) wake up and complete the morning routine at 4:00 am, 2)"""

print("【完整 prompt 预估】")
print(f"prompt 字符数: {len(prompt_template)}")
print(f"占 8000 字符上限的: {len(prompt_template)/8000*100:.1f}%")
print()
print("【结论】")
if len(prompt_template) < 8000:
    print(f"✅ 安全！prompt ({len(prompt_template)} 字符) 远小于 8000 上限")
    print(f"   剩余空间: {8000 - len(prompt_template)} 字符")
else:
    print(f"⚠️ 危险！prompt ({len(prompt_template)} 字符) 超过 8000 上限")
