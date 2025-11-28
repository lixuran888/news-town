"""
Quick test script - test backend logic without starting services
Usage: python quick_test.py
"""
import json
import os
import sys

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path for sentiment module
sys.path.insert(0, r"e:\generative_agents-main\generative_agents-main\reverie\backend_server")

# Switch to frontend_server directory (simulate Django working directory)
os.chdir(r"e:\generative_agents-main\environment\frontend_server")

def test_persona_state(sim_code, persona_name):
    """模拟 views.py 的 replay_persona_state 逻辑"""
    print(f"\n{'='*50}")
    print(f"测试: {persona_name} @ {sim_code}")
    print("="*50)
    
    # 1. 查找路径
    possible_paths = [
        f"storage/{sim_code}/personas/{persona_name}/bootstrap_memory",
        f"storage/{sim_code}/personas/{persona_name}",
        f"compressed_storage/{sim_code}/personas/{persona_name}/bootstrap_memory",
        f"storage/base_the_ville_clean/personas/{persona_name}/bootstrap_memory",
    ]
    
    memory = None
    for path in possible_paths:
        scratch_path = path + "/scratch.json"
        if os.path.exists(scratch_path):
            memory = path
            print(f"✓ 找到路径: {path}")
            break
        else:
            print(f"✗ 不存在: {path}")
    
    if not memory:
        print("❌ 错误: 找不到 persona 数据!")
        return False
    
    # 2. 加载文件
    try:
        with open(memory + "/scratch.json", encoding="utf-8") as f:
            scratch = json.load(f)
        print(f"✓ scratch.json 加载成功")
    except Exception as e:
        print(f"❌ scratch.json 加载失败: {e}")
        return False
    
    try:
        with open(memory + "/spatial_memory.json", encoding="utf-8") as f:
            spatial = json.load(f)
        print(f"✓ spatial_memory.json 加载成功")
    except Exception as e:
        print(f"❌ spatial_memory.json 加载失败: {e}")
        return False
    
    try:
        with open(memory + "/associative_memory/nodes.json", encoding="utf-8") as f:
            associative = json.load(f)
        print(f"✓ nodes.json 加载成功, 类型: {type(associative).__name__}")
    except Exception as e:
        print(f"❌ nodes.json 加载失败: {e}")
        return False
    
    # 3. 处理 associative memory（测试空列表处理）
    a_mem_event = []
    a_mem_chat = []
    a_mem_thought = []
    
    if isinstance(associative, dict) and associative:
        for count in range(len(associative.keys()), 0, -1):
            node_id = f"node_{str(count)}"
            node_details = associative.get(node_id)
            if not node_details:
                continue
            if node_details.get("type") == "event":
                a_mem_event.append(node_details)
            elif node_details.get("type") == "chat":
                a_mem_chat.append(node_details)
            elif node_details.get("type") == "thought":
                a_mem_thought.append(node_details)
        print(f"✓ 解析记忆: {len(a_mem_event)} events, {len(a_mem_chat)} chats, {len(a_mem_thought)} thoughts")
    else:
        print(f"✓ 空记忆（正常，新角色）")
    
    # 4. 显示关键信息
    print(f"\n--- Persona 状态 ---")
    print(f"  名字: {scratch.get('name')}")
    print(f"  当前动作: {scratch.get('act_description', '(空)')}")
    print(f"  位置: {scratch.get('act_address', '(空)')}")
    print(f"  living_area: {scratch.get('living_area')}")
    
    return True


def test_sentiment_model():
    """测试情感分析模块"""
    print("\n" + "="*50)
    print("情感分析模块测试")
    print("="*50)
    
    try:
        from sentiment.sentiment_analysis import analyze_sentiment, _load_model, _use_simple_mode
        
        # 加载模型
        model = _load_model()
        
        # 检查是否使用 HuggingFace
        from sentiment import sentiment_analysis
        if sentiment_analysis._use_simple_mode:
            print("⚠️  使用: 关键词模式（降级）")
            print("   原因: HuggingFace transformers 不可用")
        else:
            print("✅ 使用: HuggingFace 模型（准确率~88%）")
        
        # 测试几个例句
        test_sentences = [
            "我很担心这次食物中毒事件会影响孩子们的健康",
            "政府的处理措施很及时，我感到很安心",
            "今天天气不错，适合去公园散步",
            "这件事太可怕了，必须严肃处理！",
        ]
        
        print("\n--- 情感分析测试 ---")
        for sent in test_sentences:
            result = analyze_sentiment(sent)
            emoji = "😊" if result["label"] == "positive" else "😟" if result["label"] == "negative" else "😐"
            print(f"  {emoji} [{result['label']:8}] {result['score']:+.2f} | {sent[:30]}...")
        
        return True
    except Exception as e:
        print(f"❌ 情感模块加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_chat_history(sim_code, persona_name):
    """显示 persona 的对话历史（带情感标签）"""
    print(f"\n--- {persona_name} 对话历史 ---")
    
    memory_path = f"storage/{sim_code}/personas/{persona_name}/bootstrap_memory"
    nodes_path = memory_path + "/associative_memory/nodes.json"
    
    if not os.path.exists(nodes_path):
        print("  (无对话记录)")
        return
    
    with open(nodes_path, encoding="utf-8") as f:
        nodes = json.load(f)
    
    if not isinstance(nodes, dict) or not nodes:
        print("  (无对话记录)")
        return
    
    # 提取 chat 类型的记录
    chats = []
    for node_id, node in nodes.items():
        if node.get("type") == "chat":
            chats.append(node)
    
    if not chats:
        print("  (无对话记录)")
        return
    
    # 显示最近的对话（最多5条）
    try:
        from sentiment.sentiment_analysis import analyze_sentiment
        has_sentiment = True
    except:
        has_sentiment = False
    
    print(f"  共 {len(chats)} 条对话，显示最近 5 条:")
    for chat in chats[-5:]:
        desc = chat.get("description", "")[:60]
        if has_sentiment:
            result = analyze_sentiment(desc)
            emoji = "😊" if result["label"] == "positive" else "😟" if result["label"] == "negative" else "😐"
            print(f"    {emoji} {desc}...")
        else:
            print(f"    {desc}...")


def simulate_state_details(sim_code, persona_name):
    """模拟 State Details 弹窗显示的内容"""
    print(f"\n{'='*50}")
    print(f"📋 State Details: {persona_name}")
    print("="*50)
    
    memory_path = f"storage/{sim_code}/personas/{persona_name}/bootstrap_memory"
    
    # 加载 scratch
    try:
        with open(memory_path + "/scratch.json", encoding="utf-8") as f:
            scratch = json.load(f)
    except Exception as e:
        print(f"❌ 加载失败: {e}")
        return False
    
    # 模拟弹窗内容
    print(f"\n【基本信息】")
    print(f"  姓名: {scratch.get('name')}")
    print(f"  年龄: {scratch.get('age')}")
    print(f"  性格: {scratch.get('innate')}")
    
    print(f"\n【当前状态】")
    print(f"  当前动作: {scratch.get('act_description') or '(暂无)'}")
    print(f"  位置: {scratch.get('act_address') or '(暂无)'}")
    print(f"  正在交谈: {scratch.get('chatting_with') or '(无)'}")
    
    print(f"\n【日程安排】")
    daily = scratch.get('f_daily_schedule_hourly_org', [])
    if daily:
        for item in daily[:5]:
            print(f"    {item}")
        if len(daily) > 5:
            print(f"    ... 共 {len(daily)} 项")
    else:
        print("    (暂无)")
    
    # 加载记忆统计
    try:
        with open(memory_path + "/associative_memory/nodes.json", encoding="utf-8") as f:
            nodes = json.load(f)
        if isinstance(nodes, dict):
            events = sum(1 for n in nodes.values() if n.get("type") == "event")
            chats = sum(1 for n in nodes.values() if n.get("type") == "chat")
            thoughts = sum(1 for n in nodes.values() if n.get("type") == "thought")
            print(f"\n【记忆统计】")
            print(f"  事件: {events} | 对话: {chats} | 想法: {thoughts}")
    except:
        pass
    
    return True


def analyze_all_chats(sim_code):
    """分析所有人的对话并做情感统计，写入专家记忆"""
    print("\n\n" + "#"*60)
    print("# 全员对话情感分析 & 专家记忆写入")
    print("#"*60)
    
    # 导入 collect_opinions 的函数
    sys.path.insert(0, r"e:\generative_agents-main")
    from collect_opinions import collect_all_chats, analyze_and_summarize, write_to_expert_memory, EXPERTS
    
    # 收集所有对话
    sim_path = f"storage/{sim_code}"
    all_chats, _ = collect_all_chats(sim_path)
    
    if not all_chats:
        print("\n(暂无对话记录)")
        return
    
    print(f"\n总对话数: {len(all_chats)}")
    
    # 分析情感
    summary = analyze_and_summarize(all_chats)
    overall = summary["overall"]
    by_persona = summary["by_persona"]
    
    # 显示统计
    print("\n" + "=" * 70)
    print("按角色情感统计 (排除专家)")
    print("=" * 70)
    print(f"{'角色':35} | {'😊正面':8} | {'😐中性':8} | {'😟负面':8} | {'总计':6}")
    print("-" * 70)
    
    for persona, stats in sorted(by_persona.items(), key=lambda x: x[1]["total"], reverse=True):
        if stats["total"] > 0:
            print(f"{persona:35} | {stats['positive']:8} | {stats['neutral']:8} | {stats['negative']:8} | {stats['total']:6}")
    
    print("-" * 70)
    print(f"{'总计':35} | {overall['positive']:8} | {overall['neutral']:8} | {overall['negative']:8} | {overall['total']:6}")
    
    if overall['total'] > 0:
        print(f"\n情感分布: 😊{overall['positive']/overall['total']*100:.1f}% | 😐{overall['neutral']/overall['total']*100:.1f}% | 😟{overall['negative']/overall['total']*100:.1f}%")
        print(f"整体趋势: {overall['trend']}")
    
    # 显示一些示例
    print("\n" + "=" * 70)
    print("情感示例 (最近 10 条)")
    print("=" * 70)
    for item in summary["all_utterances"][-10:]:
        s = item["sentiment"]
        emoji = "😊" if s["label"] == "positive" else ("😟" if s["label"] == "negative" else "😐")
        print(f"{emoji} [{s['label']:8}] {item['speaker']}: {item['text'][:50]}...")
    
    # 写入专家记忆
    print("\n" + "=" * 70)
    print("写入专家记忆 (会议前民意收集)")
    print("=" * 70)
    
    from pathlib import Path
    sim_full_path = Path(r'e:\generative_agents-main\environment\frontend_server') / sim_path
    written = write_to_expert_memory(sim_full_path, summary)
    print(f"\n✅ 已写入 {len(written)}/{len(EXPERTS)} 个专家的记忆")


def main():
    # 获取最新的有效模拟
    from pathlib import Path
    storage_dir = Path("storage")
    valid = []
    for p in storage_dir.iterdir():
        if not p.is_dir():
            continue
        personas_dir = p / "personas"
        if personas_dir.exists():
            for persona in personas_dir.iterdir():
                if (persona / "bootstrap_memory" / "scratch.json").exists():
                    valid.append(p)
                    break
    valid.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not valid:
        print("没有找到有效的模拟目录!")
        return
    
    latest_sim = valid[0].name
    print(f"最新模拟: {latest_sim}")
    
    # 1. 测试情感模块
    test_sentiment_model()
    
    # 2. 测试文件加载
    experts = [
        "Public Health Expert",  # 这个有历史数据
        "Market Supervision Expert",
        "Isabella Rodriguez",
    ]
    
    print("\n" + "="*50)
    print("文件加载测试")
    print("="*50)
    results = []
    for expert in experts:
        ok = test_persona_state(latest_sim, expert)
        results.append((expert, ok))
    
    # 3. 显示对话历史（带情感）
    for expert in experts:
        show_chat_history(latest_sim, expert)
    
    # 4. 模拟 State Details 弹窗
    print("\n\n" + "#"*60)
    print("# 模拟 State Details 弹窗")
    print("#"*60)
    simulate_state_details(latest_sim, "Public Health Expert")
    
    # 5. 分析所有人的对话
    analyze_all_chats(latest_sim)
    
    # 汇总
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}: {name}")


if __name__ == "__main__":
    main()
