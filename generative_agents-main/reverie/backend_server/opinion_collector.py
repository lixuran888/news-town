"""
Opinion Collector Module
在会议前自动收集所有民众的言论和情感分析，写入专家记忆
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# 专家列表
EXPERTS = [
    "Public Health Expert",
    "Market Supervision Expert", 
    "Education Bureau Representative",
    "Meeting Moderator"
]

# 导入情感分析
try:
    from sentiment.sentiment_analysis import analyze_sentiment
    SENTIMENT_ENABLED = True
except ImportError:
    SENTIMENT_ENABLED = False
    print("[OpinionCollector] 情感分析模块不可用，使用关键词模式")


def simple_sentiment(text):
    """简单关键词情感分析（降级模式）"""
    negative_words = ["担心", "害怕", "可怕", "严重", "糟糕", "不满", "生气", "愤怒", "失望", "worried", "afraid", "terrible"]
    positive_words = ["好", "高兴", "感谢", "满意", "支持", "开心", "放心", "happy", "good", "thank", "glad"]
    
    text_lower = text.lower()
    neg_count = sum(1 for w in negative_words if w in text_lower)
    pos_count = sum(1 for w in positive_words if w in text_lower)
    
    if neg_count > pos_count:
        return {"label": "negative", "score": -0.8}
    elif pos_count > neg_count:
        return {"label": "positive", "score": 0.8}
    else:
        return {"label": "neutral", "score": 0.0}


def collect_opinions_from_personas(personas, curr_time):
    """
    从所有 persona 的 event_opinions 中收集事件相关舆论
    (新版：使用预提取的舆论观点，而非解析原始对话)
    
    Args:
        personas: dict of {name: Persona object}
        curr_time: 当前模拟时间
    
    Returns:
        all_utterances: list of {speaker, text, sentiment, stance}
        by_persona: dict of {name: {positive, negative, neutral, total, stances}}
    """
    all_utterances = []
    by_persona = defaultdict(lambda: {
        "positive": 0, "negative": 0, "neutral": 0, "total": 0,
        "stances": {"supportive": 0, "critical": 0, "worried": 0, "neutral": 0, "angry": 0}
    })
    
    seen_opinions = set()  # 避免重复
    
    # 遍历所有 persona 的 event_opinions
    for persona_name, persona in personas.items():
        # 跳过专家
        if persona_name in EXPERTS:
            continue
        
        try:
            # 获取预提取的事件舆论观点
            event_opinions = getattr(persona.scratch, 'event_opinions', [])
            
            for opinion_data in event_opinions:
                speaker = opinion_data.get("speaker", persona_name)
                opinion_text = opinion_data.get("opinion", "")
                stance = opinion_data.get("stance", "neutral")
                
                # 跳过空的或无效的
                if not opinion_text or "no clear opinion" in opinion_text.lower():
                    continue
                
                # 避免重复
                opinion_key = f"{speaker}:{opinion_text[:50]}"
                if opinion_key in seen_opinions:
                    continue
                seen_opinions.add(opinion_key)
                
                # 根据 stance 映射到情感
                stance_to_sentiment = {
                    "supportive": {"label": "positive", "score": 0.8},
                    "critical": {"label": "negative", "score": -0.8},
                    "worried": {"label": "negative", "score": -0.5},
                    "angry": {"label": "negative", "score": -0.9},
                    "neutral": {"label": "neutral", "score": 0.0}
                }
                sentiment = stance_to_sentiment.get(stance, {"label": "neutral", "score": 0.0})
                
                label = sentiment["label"]
                by_persona[speaker][label] += 1
                by_persona[speaker]["total"] += 1
                by_persona[speaker]["stances"][stance] += 1
                
                all_utterances.append({
                    "speaker": speaker,
                    "text": opinion_text,
                    "sentiment": sentiment,
                    "stance": stance
                })
                
        except Exception as e:
            print(f"  [OpinionCollector] Warning: {persona_name} - {e}")
            pass
    
    return all_utterances, dict(by_persona)


def generate_opinion_summary(all_utterances, by_persona, curr_time):
    """
    生成民意摘要文本
    """
    total_pos = sum(s["positive"] for s in by_persona.values())
    total_neg = sum(s["negative"] for s in by_persona.values())
    total_neu = sum(s["neutral"] for s in by_persona.values())
    total_all = total_pos + total_neg + total_neu
    
    # 判断整体趋势
    if total_all > 0:
        if total_pos > total_neg * 1.5:
            trend = "积极 (Positive)"
        elif total_neg > total_pos * 1.5:
            trend = "消极 (Negative)"
        else:
            trend = "中性偏稳 (Neutral)"
    else:
        trend = "无数据"
    
    time_str = curr_time.strftime("%H:%M") if curr_time else "unknown"
    
    summary = f"""[Public Opinion Report - Before Meeting]
Collection Time: {time_str}
Total Utterances: {total_all}
Sentiment Distribution: 
  - Positive: {total_pos} ({total_pos/max(1,total_all)*100:.0f}%)
  - Neutral: {total_neu} ({total_neu/max(1,total_all)*100:.0f}%)
  - Negative: {total_neg} ({total_neg/max(1,total_all)*100:.0f}%)
Overall Trend: {trend}

Resident Sentiment Summary:"""
    
    for name, stats in sorted(by_persona.items(), key=lambda x: x[1]["total"], reverse=True):
        if stats["total"] > 0:
            main = "Positive" if stats["positive"] > stats["negative"] else ("Negative" if stats["negative"] > stats["positive"] else "Neutral")
            summary += f"\n  - {name}: {main} ({stats['positive']}+/{stats['neutral']}o/{stats['negative']}-)"
    
    # 关键发言
    summary += "\n\nKey Utterances:"
    pos_utts = [u for u in all_utterances if u["sentiment"]["label"] == "positive"][:3]
    neg_utts = [u for u in all_utterances if u["sentiment"]["label"] == "negative"][:3]
    
    for u in pos_utts:
        summary += f"\n  [+] {u['speaker']}: \"{u['text'][:80]}...\""
    for u in neg_utts:
        summary += f"\n  [-] {u['speaker']}: \"{u['text'][:80]}...\""
    
    return summary, trend


def inject_opinion_to_experts(personas, summary_text, curr_time):
    """
    将民意摘要注入到所有专家的记忆中
    通过修改 scratch.currently 来影响专家的行为
    
    Args:
        personas: dict of {name: Persona object}
        summary_text: 民意摘要文本
        curr_time: 当前模拟时间
    """
    injected = []
    
    for expert_name in EXPERTS:
        if expert_name not in personas:
            continue
        
        expert = personas[expert_name]
        
        try:
            if hasattr(expert, 'scratch'):
                # 方法1: 添加到 scratch 的 opinion_report 字段（新增）
                expert.scratch.opinion_report = summary_text
                
                # 方法2: 更新 currently 字段，让专家意识到民意
                original_currently = expert.scratch.currently or ""
                short_summary = f"Based on collected public opinions (trend: see report), "
                if "opinion" not in original_currently.lower():
                    expert.scratch.currently = short_summary + original_currently
                
                # 方法3: 添加到 daily_req 中作为当天任务
                # （可选，暂不启用）
                
                injected.append(expert_name)
                print(f"  [OpinionCollector] ✓ Injected opinion report to {expert_name}")
                    
        except Exception as e:
            print(f"  [OpinionCollector] ✗ Failed to inject to {expert_name}: {e}")
    
    return injected


def collect_and_inject_opinions(personas, curr_time):
    """
    主函数：收集民意并注入专家记忆
    在会议前调用此函数
    
    Args:
        personas: dict of {name: Persona object}
        curr_time: 当前模拟时间
    
    Returns:
        bool: 是否成功
    """
    print(f"\n[OpinionCollector] === Starting opinion collection at {curr_time} ===")
    
    # 1. 收集所有言论
    all_utterances, by_persona = collect_opinions_from_personas(personas, curr_time)
    
    if not all_utterances:
        print("[OpinionCollector] No utterances found, skipping")
        return False
    
    print(f"[OpinionCollector] Collected {len(all_utterances)} utterances from {len(by_persona)} residents")
    
    # 2. 生成摘要
    summary_text, trend = generate_opinion_summary(all_utterances, by_persona, curr_time)
    print(f"[OpinionCollector] Overall trend: {trend}")
    
    # 3. 注入专家记忆
    injected = inject_opinion_to_experts(personas, summary_text, curr_time)
    print(f"[OpinionCollector] Injected to {len(injected)} experts: {injected}")
    
    print("[OpinionCollector] === Done ===\n")
    return True
