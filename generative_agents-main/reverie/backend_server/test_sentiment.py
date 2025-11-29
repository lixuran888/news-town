# -*- coding: utf-8 -*-
"""
快速测试情感分析模块 - 多模型对比
运行: python test_sentiment.py
"""

import sys
sys.path.append('.')

# 模拟对话（关于食物中毒事件 + 日常话题）
test_conversations = [
    ("Maria", "你听说那个食物中毒的事了吗？好可怕，学校真的应该负责！"),
    ("Klaus", "是啊，我也很担心。那些学生太可怜了，希望他们早日康复。"),
    ("Maria", "不过政府说会调查处理，希望能有个交代。"),
    ("Klaus", "嗯，我们也只能等消息了。对了，你最近物理作业写完了吗？"),
    ("Maria", "还没呢！那个量子力学太难了，你能帮我看看吗？"),
    ("Klaus", "没问题！我们去 Hobbs Cafe 一起讨论吧，顺便喝杯咖啡。"),
    ("Maria", "太好了！Isabella 做的拿铁超好喝！"),
    ("Klaus", "哈哈，走吧！"),
]

# 人工标注的期望情感（作为参考）
expected = ["negative", "negative", "neutral", "neutral", "neutral", "positive", "positive", "positive"]

def get_emoji(label):
    if label == "positive": return "😊"
    elif label == "negative": return "😟"
    else: return "😐"

# ============ 方法1: SnowNLP ============
print("=" * 70)
print("【方法1: SnowNLP（中文情感分析专用）】")
print("-" * 70)

try:
    from snownlp import SnowNLP
    snownlp_ok = True
    
    snownlp_results = []
    for i, (speaker, utt) in enumerate(test_conversations):
        s = SnowNLP(utt)
        raw = s.sentiments  # 0-1, 0=负面, 1=正面
        score = (raw - 0.5) * 2  # 转为 -1 到 1
        
        if score > 0.2: label = "positive"
        elif score < -0.2: label = "negative"
        else: label = "neutral"
        
        match = "✓" if label == expected[i] else "✗"
        emoji = get_emoji(label)
        print(f"{match} {speaker}: {utt[:30]}...")
        print(f"     [{emoji} {label} {score:+.2f}] (期望: {expected[i]})")
        snownlp_results.append(label)
    
    correct = sum(1 for i in range(len(expected)) if snownlp_results[i] == expected[i])
    print(f"\n准确率: {correct}/{len(expected)} = {correct/len(expected)*100:.0f}%")
except ImportError:
    print("❌ SnowNLP 未安装，跳过")
    snownlp_ok = False

# ============ 方法2: 关键词模式 ============
print("\n" + "=" * 70)
print("【方法2: 关键词模式（简单匹配）】")
print("-" * 70)

negative_words = ["担心", "害怕", "可怕", "中毒", "难", "糟糕", "问题", "负责", "可怜"]
positive_words = ["好", "棒", "开心", "高兴", "太好了", "没问题", "希望", "好喝", "哈哈"]

keyword_results = []
for i, (speaker, utt) in enumerate(test_conversations):
    neg = sum(1 for w in negative_words if w in utt)
    pos = sum(1 for w in positive_words if w in utt)
    
    if pos > neg: label = "positive"
    elif neg > pos: label = "negative"
    else: label = "neutral"
    
    score = (pos - neg) / max(pos + neg, 1)
    
    match = "✓" if label == expected[i] else "✗"
    emoji = get_emoji(label)
    print(f"{match} {speaker}: {utt[:30]}...")
    print(f"     [{emoji} {label} {score:+.2f}] (期望: {expected[i]})")
    keyword_results.append(label)

correct = sum(1 for i in range(len(expected)) if keyword_results[i] == expected[i])
print(f"\n准确率: {correct}/{len(expected)} = {correct/len(expected)*100:.0f}%")

# ============ 方法3: HuggingFace (lxyuan) ============
print("\n" + "=" * 70)
print("【方法3: HuggingFace (lxyuan/distilbert)】")
print("-" * 70)

hf_ok = False
hf_results = []
try:
    # 先测试能否导入
    print("正在导入 transformers...")
    import transformers
    print(f"transformers 版本: {transformers.__version__}")
    
    from transformers import pipeline
    print("pipeline 导入成功，正在加载模型...")
    
    classifier = pipeline(
        "sentiment-analysis",
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student"
    )
    print("模型加载成功！\n")
    hf_ok = True
    
    for i, (speaker, utt) in enumerate(test_conversations):
        result = classifier(utt[:512])[0]
        raw_label = result["label"].lower()
        
        if raw_label == "positive": label = "positive"
        elif raw_label == "negative": label = "negative"
        else: label = "neutral"
        
        match = "✓" if label == expected[i] else "✗"
        emoji = get_emoji(label)
        print(f"{match} {speaker}: {utt[:30]}...")
        print(f"     [{emoji} {label} {result['score']:.2f}] (期望: {expected[i]})")
        hf_results.append(label)
    
    correct = sum(1 for i in range(len(expected)) if hf_results[i] == expected[i])
    print(f"\n准确率: {correct}/{len(expected)} = {correct/len(expected)*100:.0f}%")

except ImportError as e:
    print(f"❌ 导入失败: {e}")
except Exception as e:
    print(f"❌ 加载失败: {e}")

# ============ 总结 ============
print("\n" + "=" * 70)
print("【总结】")
print("-" * 70)
print(f"期望标签:   {expected}")
if snownlp_ok:
    print(f"SnowNLP:    {snownlp_results}")
print(f"关键词模式: {keyword_results}")
if hf_ok:
    print(f"HuggingFace: {hf_results}")
print("=" * 70)
