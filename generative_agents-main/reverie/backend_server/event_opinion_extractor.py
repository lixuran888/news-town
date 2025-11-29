"""
Event Opinion Extractor
从对话中提取与事件相关的舆论观点
"""
import re
from datetime import datetime

# 事件相关关键词
EVENT_KEYWORDS = [
    # 英文
    "food poisoning", "poisoning", "sick", "hospital", "cafeteria", 
    "safety", "incident", "school meal", "contaminated", "ill",
    "vomit", "diarrhea", "health", "outbreak", "emergency",
    # 中文
    "食物中毒", "中毒", "生病", "医院", "食堂", "安全", 
    "事件", "学校餐", "污染", "呕吐", "腹泻", "健康",
    "爆发", "紧急", "餐厅", "卫生"
]

# 最大对话轮数（防止 token 超限）
MAX_UTTERANCES = 10


def is_event_related(text):
    """检查文本是否与事件相关"""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in EVENT_KEYWORDS)


def truncate_conversation(all_utt, max_lines=MAX_UTTERANCES):
    """截断过长的对话，保留最后 N 轮"""
    lines = all_utt.strip().split('\n')
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
        return '\n'.join(lines)
    return all_utt


def extract_event_opinion(persona, all_utt, other_name):
    """
    从对话中提取事件相关的舆论观点
    
    Args:
        persona: 当前 persona 对象
        all_utt: 完整对话文本 "Name: utterance\nName: utterance..."
        other_name: 对话对象名字
    
    Returns:
        dict: {speaker, opinion, stance, time} 或 None
    """
    # 1. 检查是否与事件相关
    if not is_event_related(all_utt):
        return None
    
    # 2. 截断过长对话
    truncated_utt = truncate_conversation(all_utt, MAX_UTTERANCES)
    
    # 3. 调用 LLM 提取观点
    try:
        from persona.prompt_template.gpt_structure import ChatGPT_single_request
        
        prompt = f"""Based on this conversation about a campus food poisoning incident, extract the speaker's opinion and stance.

[Conversation]
{truncated_utt}

Focus on {persona.scratch.name}'s view about the food poisoning incident.

Output format (one line only):
{{opinion in 1-2 sentences}} | stance: {{supportive/critical/worried/neutral/angry}}

Example outputs:
- "believes school should close cafeteria for inspection | stance: critical"
- "is worried about student health but trusts school will handle it | stance: worried"
- "thinks the situation is being exaggerated | stance: neutral"

If the conversation doesn't express a clear opinion about the incident, output:
"no clear opinion expressed | stance: neutral"

{persona.scratch.name}'s opinion:"""

        response = ChatGPT_single_request(prompt)
        
        if response and response.strip():
            # 解析响应
            response = response.strip().strip('"')
            
            # 提取 stance
            stance = "neutral"
            if "| stance:" in response.lower():
                parts = response.split("| stance:")
                opinion_text = parts[0].strip()
                stance = parts[1].strip().lower() if len(parts) > 1 else "neutral"
            else:
                opinion_text = response
            
            # 清理 stance
            valid_stances = ["supportive", "critical", "worried", "neutral", "angry"]
            if stance not in valid_stances:
                stance = "neutral"
            
            return {
                "speaker": persona.scratch.name,
                "other": other_name,
                "opinion": opinion_text,
                "stance": stance,
                "time": persona.scratch.curr_time.strftime("%H:%M") if persona.scratch.curr_time else "unknown"
            }
    
    except Exception as e:
        print(f"[EventOpinion] Error extracting opinion: {e}")
        return None
    
    return None


def save_event_opinion(persona, opinion_data):
    """
    将舆论观点保存到 persona.scratch
    
    Args:
        persona: persona 对象
        opinion_data: extract_event_opinion 返回的 dict
    """
    if not opinion_data:
        return
    
    # 初始化 event_opinions 列表
    if not hasattr(persona.scratch, 'event_opinions'):
        persona.scratch.event_opinions = []
    
    # 避免重复
    existing = [o.get("opinion", "")[:50] for o in persona.scratch.event_opinions]
    if opinion_data["opinion"][:50] not in existing:
        persona.scratch.event_opinions.append(opinion_data)
        print(f"[EventOpinion] Saved: {persona.scratch.name} - {opinion_data['stance']} - {opinion_data['opinion'][:50]}...")


def extract_and_save_opinion(persona, all_utt, other_name):
    """
    主函数：提取并保存舆论观点（在对话后调用）
    
    Args:
        persona: 当前 persona 对象
        all_utt: 完整对话文本
        other_name: 对话对象名字
    
    Returns:
        bool: 是否成功提取并保存
    """
    opinion_data = extract_event_opinion(persona, all_utt, other_name)
    
    if opinion_data and opinion_data.get("opinion") and "no clear opinion" not in opinion_data["opinion"].lower():
        save_event_opinion(persona, opinion_data)
        return True
    
    return False
