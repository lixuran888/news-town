import json, sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

# 专家列表
EXPERTS = [
    "Public Health Expert",
    "Market Supervision Expert", 
    "Education Bureau Representative",
    "Meeting Moderator"
]

def collect_all_chats(sim_dir=None):
    """
    收集所有人的对话记录
    返回: [(persona_name, chat_description, chat_filling, created_time), ...]
    """
    if sim_dir is None:
        # 找最新的模拟
        storage = Path(r'e:\generative_agents-main\environment\frontend_server\storage')
        sims = sorted([p for p in storage.iterdir() if p.is_dir() and p.name.startswith('auto_run')], 
                      key=lambda p: p.stat().st_mtime, reverse=True)
        if not sims:
            return [], ""
        sim_dir = sims[0]
    else:
        sim_dir = Path(sim_dir)
    
    personas_dir = sim_dir / "personas"
    all_chats = []
    
    for persona_dir in sorted(personas_dir.iterdir()):
        if not persona_dir.is_dir():
            continue
        
        nodes_path = persona_dir / "bootstrap_memory" / "associative_memory" / "nodes.json"
        if not nodes_path.exists():
            continue
            
        with open(nodes_path, encoding='utf-8') as f:
            nodes = json.load(f)
        
        if not isinstance(nodes, dict) or not nodes:
            continue
        
        # 收集 chat 类型的记忆
        for node_id, node in nodes.items():
            if node.get("type") == "chat":
                all_chats.append({
                    "persona": persona_dir.name,
                    "description": node.get("description", ""),
                    "filling": node.get("filling", []),
                    "created": node.get("created", ""),
                    "node_id": node_id
                })
    
    # 按时间排序
    all_chats.sort(key=lambda x: x["created"])
    return all_chats, sim_dir.name


def analyze_and_summarize(all_chats):
    """
    分析所有对话的情感，生成民意摘要
    返回: {
        "by_persona": {name: {positive, negative, neutral, total, utterances}},
        "overall": {positive, negative, neutral, total, trend},
        "key_opinions": [最重要的发言]
    }
    """
    # 导入情感分析模块
    sys.path.insert(0, r"e:\generative_agents-main\generative_agents-main\reverie\backend_server")
    try:
        from sentiment.sentiment_analysis import analyze_sentiment
        SENTIMENT_OK = True
    except:
        SENTIMENT_OK = False
        print("⚠️ 情感分析模块不可用，使用简单模式")
    
    by_persona = defaultdict(lambda: {
        "positive": 0, "negative": 0, "neutral": 0, "total": 0,
        "utterances": []
    })
    all_utterances = []
    
    for chat in all_chats:
        filling = chat.get("filling", [])
        for speaker, utt in filling:
            if speaker in EXPERTS:  # 跳过专家自己的发言
                continue
            
            if SENTIMENT_OK:
                sentiment = analyze_sentiment(utt)
            else:
                # 简单关键词模式
                sentiment = {"label": "neutral", "score": 0.0}
                if any(w in utt for w in ["担心", "害怕", "可怕", "严重", "糟糕"]):
                    sentiment = {"label": "negative", "score": -0.8}
                elif any(w in utt for w in ["好", "高兴", "感谢", "满意", "支持"]):
                    sentiment = {"label": "positive", "score": 0.8}
            
            label = sentiment["label"]
            by_persona[speaker][label] += 1
            by_persona[speaker]["total"] += 1
            by_persona[speaker]["utterances"].append({
                "text": utt,
                "sentiment": sentiment
            })
            all_utterances.append({
                "speaker": speaker,
                "text": utt,
                "sentiment": sentiment
            })
    
    # 总体统计
    total_pos = sum(s["positive"] for s in by_persona.values())
    total_neg = sum(s["negative"] for s in by_persona.values())
    total_neu = sum(s["neutral"] for s in by_persona.values())
    total_all = total_pos + total_neg + total_neu
    
    if total_all > 0:
        if total_pos > total_neg * 1.5:
            trend = "积极"
        elif total_neg > total_pos * 1.5:
            trend = "消极"
        else:
            trend = "中性偏稳"
    else:
        trend = "无数据"
    
    return {
        "by_persona": dict(by_persona),
        "overall": {
            "positive": total_pos,
            "negative": total_neg,
            "neutral": total_neu,
            "total": total_all,
            "trend": trend
        },
        "all_utterances": all_utterances
    }


def write_to_expert_memory(sim_dir, summary):
    """
    将民意收集结果写入所有专家的记忆中
    """
    sim_path = Path(sim_dir) if isinstance(sim_dir, str) else sim_dir
    if not sim_path.is_absolute():
        sim_path = Path(r'e:\generative_agents-main\environment\frontend_server\storage') / sim_path
    
    # 生成记忆内容
    overall = summary["overall"]
    by_persona = summary["by_persona"]
    
    # 民意摘要文本
    opinion_summary = f"""[会议前民意收集报告]
收集时间: 11:00 会议开始前
总发言数: {overall['total']} 条
情感分布: 积极 {overall['positive']} 条 ({overall['positive']/max(1,overall['total'])*100:.0f}%) | 中性 {overall['neutral']} 条 | 消极 {overall['negative']} 条 ({overall['negative']/max(1,overall['total'])*100:.0f}%)
整体情感趋势: {overall['trend']}

各居民情感倾向:"""
    
    for name, stats in sorted(by_persona.items(), key=lambda x: x[1]["total"], reverse=True):
        if stats["total"] > 0:
            main_sentiment = "积极" if stats["positive"] > stats["negative"] else ("消极" if stats["negative"] > stats["positive"] else "中性")
            opinion_summary += f"\n  - {name}: {main_sentiment} ({stats['positive']}正/{stats['neutral']}中/{stats['negative']}负)"
    
    # 添加关键发言摘录
    opinion_summary += "\n\n关键发言摘录:"
    utterances = summary.get("all_utterances", [])
    # 选择最有代表性的发言（正面和负面各取几条）
    pos_utts = [u for u in utterances if u["sentiment"]["label"] == "positive"][:3]
    neg_utts = [u for u in utterances if u["sentiment"]["label"] == "negative"][:3]
    
    for u in pos_utts:
        opinion_summary += f"\n  😊 {u['speaker']}: \"{u['text'][:60]}...\""
    for u in neg_utts:
        opinion_summary += f"\n  😟 {u['speaker']}: \"{u['text'][:60]}...\""
    
    # 写入每个专家的记忆
    written = []
    for expert in EXPERTS:
        nodes_path = sim_path / "personas" / expert / "bootstrap_memory" / "associative_memory" / "nodes.json"
        
        if not nodes_path.exists():
            print(f"  ⚠️ {expert}: 文件不存在")
            continue
        
        try:
            with open(nodes_path, encoding='utf-8') as f:
                nodes = json.load(f)
            
            # 如果是空列表，转换为字典
            if isinstance(nodes, list):
                nodes = {}
            
            # 找到最大的 node_id
            max_id = 0
            for key in nodes.keys():
                if key.startswith("node_"):
                    try:
                        num = int(key.split("_")[1])
                        max_id = max(max_id, num)
                    except:
                        pass
            
            # 创建新的记忆节点
            new_node_id = f"node_{max_id + 1}"
            new_node = {
                "node_count": max_id + 1,
                "type_count": 1,
                "type": "thought",
                "depth": 2,
                "created": "2023-02-13 10:55:00",  # 会议前5分钟
                "expiration": "2023-02-14 10:55:00",
                "subject": expert,
                "predicate": "collected",
                "object": "public opinions before meeting",
                "description": opinion_summary,
                "embedding_key": f"{expert} reviewed public opinions and sentiment analysis before the 11am meeting",
                "poignancy": 8,
                "keywords": ["meeting", "public opinion", "sentiment", "food poisoning"],
                "filling": []
            }
            
            nodes[new_node_id] = new_node
            
            # 写回文件
            with open(nodes_path, 'w', encoding='utf-8') as f:
                json.dump(nodes, f, ensure_ascii=False, indent=2)
            
            written.append(expert)
            print(f"  ✅ {expert}: 已写入民意收集记忆")
            
        except Exception as e:
            print(f"  ❌ {expert}: 写入失败 - {e}")
    
    return written


if __name__ == "__main__":
    print("=" * 80)
    print("收集所有人的对话记录")
    print("=" * 80)
    
    all_chats, sim_name = collect_all_chats()
    print(f"模拟: {sim_name}")
    print(f"总对话数: {len(all_chats)}")
    print()
    
    if not all_chats:
        print("(暂无对话记录)")
    else:
        # 按 persona 分组统计
        from collections import defaultdict
        by_persona = defaultdict(list)
        for chat in all_chats:
            by_persona[chat["persona"]].append(chat)
        
        print("按角色统计:")
        print("-" * 80)
        for persona, chats in sorted(by_persona.items()):
            print(f"  {persona}: {len(chats)} 条对话")
        
        print()
        print("=" * 80)
        print("所有对话内容 (按时间排序)")
        print("=" * 80)
        for i, chat in enumerate(all_chats[:20], 1):  # 只显示前 20 条
            print(f"\n[{i}] {chat['created']} - {chat['persona']}")
            print(f"    {chat['description'][:70]}...")
            if chat['filling']:
                print(f"    对话内容:")
                for speaker, utt in chat['filling'][:3]:  # 只显示前 3 句
                    print(f"      {speaker}: {utt[:50]}...")
        
        if len(all_chats) > 20:
            print(f"\n... 还有 {len(all_chats) - 20} 条对话未显示")
    
    # 保存到 JSON 供 quick_test.py 使用
    output_path = Path(r'e:\generative_agents-main\all_chats.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_chats, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已保存到 {output_path}")
    
    # 情感分析和民意收集
    if all_chats:
        print("\n" + "=" * 80)
        print("情感分析与民意收集")
        print("=" * 80)
        
        summary = analyze_and_summarize(all_chats)
        overall = summary["overall"]
        
        print(f"\n整体情感统计:")
        print(f"  😊 积极: {overall['positive']} ({overall['positive']/max(1,overall['total'])*100:.0f}%)")
        print(f"  😐 中性: {overall['neutral']} ({overall['neutral']/max(1,overall['total'])*100:.0f}%)")
        print(f"  😟 消极: {overall['negative']} ({overall['negative']/max(1,overall['total'])*100:.0f}%)")
        print(f"  📊 整体趋势: {overall['trend']}")
        
        print(f"\n各居民情感倾向:")
        for name, stats in sorted(summary["by_persona"].items(), key=lambda x: x[1]["total"], reverse=True):
            if stats["total"] > 0:
                main = "😊" if stats["positive"] > stats["negative"] else ("😟" if stats["negative"] > stats["positive"] else "😐")
                print(f"  {main} {name}: {stats['positive']}正/{stats['neutral']}中/{stats['negative']}负")
        
        # 写入专家记忆
        print("\n" + "=" * 80)
        print("写入专家记忆 (会议前民意收集)")
        print("=" * 80)
        
        # 获取模拟路径
        storage = Path(r'e:\generative_agents-main\environment\frontend_server\storage')
        sim_path = storage / sim_name
        
        written = write_to_expert_memory(sim_path, summary)
        print(f"\n✅ 已写入 {len(written)} 个专家的记忆")
