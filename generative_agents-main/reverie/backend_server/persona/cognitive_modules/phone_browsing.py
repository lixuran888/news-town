"""
phone_browsing.py

刷手机逻辑模块 - 实现线上舆论传播机制

核心功能：
1. 读取线上舆论库（最近15条）
2. 将线上内容写入个人记忆
3. 基于个人记忆和当前事件生成线上发言
4. 将发言写入线上舆论库（使用网名）
"""

import json
import os
import datetime
from pathlib import Path

# 导入必要的模块
try:
    from persona.prompt_template.gpt_structure import ChatGPT_single_request, get_embedding
except ImportError:
    try:
        import sys
        sys.path.append('../../')
        from persona.prompt_template.gpt_structure import ChatGPT_single_request, get_embedding
    except:
        def get_embedding(text):
            return [0.0] * 1536  # 占位符
        def ChatGPT_single_request(prompt):
            return "[无法连接到LLM]"

# ============================================================================
# 舆论库路径配置
# ============================================================================

def get_online_opinions_path(sim_folder=None):
    """获取线上舆论库的路径"""
    if sim_folder:
        # 运行时使用 simulation 文件夹
        return os.path.join(sim_folder, "online_opinions", "posts.json")
    else:
        # 默认使用 base 文件夹
        base_path = Path(__file__).parent.parent.parent.parent.parent.parent
        return os.path.join(
            base_path,
            "environment", "frontend_server", "storage",
            "base_the_ville_clean", "online_opinions", "posts.json"
        )

# ============================================================================
# 舆论库读写函数
# ============================================================================

def load_online_opinions(sim_folder=None):
    """加载线上舆论库"""
    path = get_online_opinions_path(sim_folder)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 返回默认结构
    return {
        "posts": [],
        "metadata": {
            "description": "线上舆论库",
            "created": datetime.datetime.now().strftime("%Y-%m-%d"),
            "total_posts": 0
        }
    }

def save_online_opinions(data, sim_folder=None):
    """保存线上舆论库"""
    path = get_online_opinions_path(sim_folder)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    data["metadata"]["total_posts"] = len(data["posts"])
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def read_recent_posts(limit=15, sim_folder=None):
    """
    读取最近的帖子
    
    Args:
        limit: 最多读取多少条（默认15条）
        sim_folder: simulation文件夹路径
    
    Returns:
        list: 最近的帖子列表
    """
    data = load_online_opinions(sim_folder)
    posts = data.get("posts", [])
    
    # 返回最近的N条（按时间倒序）
    return posts[-limit:] if len(posts) > limit else posts

def read_posts_since(since_time, sim_folder=None):
    """
    读取某个时间点之后的所有帖子（专家用）
    
    Args:
        since_time: datetime对象，读取此时间之后的帖子
        sim_folder: simulation文件夹路径
    
    Returns:
        list: 符合条件的帖子列表
    """
    data = load_online_opinions(sim_folder)
    posts = data.get("posts", [])
    
    result = []
    for post in posts:
        post_time_str = post.get("timestamp", "")
        try:
            post_time = datetime.datetime.strptime(post_time_str, "%Y-%m-%d %H:%M:%S")
            if post_time >= since_time:
                result.append(post)
        except:
            continue
    
    return result

def post_online_opinion(persona, content, sim_folder=None):
    """
    发表线上言论
    
    Args:
        persona: Persona实例
        content: 发言内容
        sim_folder: simulation文件夹路径
    
    Returns:
        dict: 新创建的帖子
    """
    data = load_online_opinions(sim_folder)
    
    # 获取网名和真名
    online_name = getattr(persona.scratch, "online_name", None)
    real_name = persona.scratch.name
    
    if not online_name:
        online_name = real_name  # 如果没有网名就用真名
    
    # 获取当前时间
    curr_time = persona.scratch.curr_time or datetime.datetime.now()
    
    # 创建新帖子
    new_post = {
        "id": len(data["posts"]) + 1,
        "online_name": online_name,
        "real_name": real_name,
        "timestamp": curr_time.strftime("%Y-%m-%d %H:%M:%S"),
        "content": content,
        "topic": "幼儿园食物中毒事件"  # 可以根据内容分析设置
    }
    
    data["posts"].append(new_post)
    save_online_opinions(data, sim_folder)
    
    print(f"[Phone] {online_name} 发帖: {content[:50]}...")
    
    return new_post

# ============================================================================
# 刷手机核心逻辑
# ============================================================================

def generate_phone_browsing_reaction(persona, recent_posts, maze=None):
    """
    生成刷手机后的反应和发言
    
    基于：
    1. 最近看到的帖子
    2. 个人记忆和性格
    3. 当前事件
    
    Returns:
        str: 要发表的内容（如果决定发言），否则None
    """
    # 构建看到的帖子内容
    posts_text = ""
    if recent_posts:
        for post in recent_posts[-10:]:  # 最多展示10条
            posts_text += f"【{post['online_name']}】: {post['content']}\n"
    else:
        posts_text = "（目前还没有人发言）"
    
    # 获取角色信息
    name = persona.scratch.name
    online_name = getattr(persona.scratch, "online_name", name)
    personality = persona.scratch.innate
    learned = persona.scratch.learned
    currently = persona.scratch.currently
    
    # 获取相关记忆
    relevant_memories = []
    try:
        retrieved = persona.a_mem.retrieve_relevant_entries(
            "幼儿园食物中毒事件", 5
        )
        for node in retrieved:
            if hasattr(node, 'description'):
                relevant_memories.append(node.description)
    except:
        pass
    
    memories_text = "\n".join(relevant_memories[:5]) if relevant_memories else "（无相关记忆）"
    
    prompt = f"""你是{name}，网名是"{online_name}"。

你的性格：{personality}
你的背景：{learned}
你现在的状态：{currently}

你最近的相关记忆：
{memories_text}

你正在刷手机，看到了以下网友的讨论：
{posts_text}

基于你的性格和立场，你会在网上发表什么看法？
要求：
1. 完全符合你的性格特点（比如暴躁的人说话冲、胆小的人可能不发言）
2. 可以表达情绪、可以骂人、可以吐槽（如果符合性格）
3. 内容要和幼儿园食物中毒事件相关
4. 字数控制在20-100字
5. 如果你性格内向或不想发言，直接回复"[不发言]"

直接输出你要发的内容（不要加引号或其他格式）："""

    try:
        response = ChatGPT_single_request(prompt)
        response = response.strip()
        
        if "[不发言]" in response or "不发言" in response or len(response) < 5:
            return None
        
        return response
    except Exception as e:
        print(f"[Phone] 生成发言失败: {e}")
        return None

def browse_phone(persona, maze=None, sim_folder=None):
    """
    刷手机主函数
    
    流程：
    1. 读取线上舆论库最近15条
    2. 将内容写入个人记忆（作为"在网上看到"的事件）
    3. 生成自己的反应/发言
    4. 将发言写入舆论库
    
    Args:
        persona: Persona实例
        maze: Maze实例（可选）
        sim_folder: simulation文件夹路径
    
    Returns:
        bool: 是否成功执行
    """
    name = persona.scratch.name
    online_name = getattr(persona.scratch, "online_name", name)
    curr_time = persona.scratch.curr_time or datetime.datetime.now()
    
    print(f"\n[Phone] === {name} 开始刷手机 ===")
    
    # 1. 读取最近的帖子
    recent_posts = read_recent_posts(limit=15, sim_folder=sim_folder)
    print(f"[Phone] 读取到 {len(recent_posts)} 条帖子")
    
    # 2. 将看到的内容写入个人记忆
    if recent_posts:
        # 生成记忆描述
        posts_summary = []
        for post in recent_posts[-5:]:  # 最近5条写入记忆
            posts_summary.append(f"{post['online_name']}说：'{post['content'][:50]}...'")
        
        memory_content = f"{name}在刷手机时看到网友们在讨论幼儿园食物中毒事件：" + "；".join(posts_summary)
        
        # 写入记忆
        try:
            created = curr_time
            expiration = curr_time + datetime.timedelta(days=30)
            s = name
            p = "browsing_phone"
            o = "online_opinions"
            
            keywords = {"phone", "online", "social_media", "food_poisoning"}
            poignancy = 5
            
            thought_embedding_pair = (memory_content, get_embedding(memory_content))
            
            persona.a_mem.add_thought(
                created, expiration, s, p, o,
                memory_content, keywords, poignancy,
                thought_embedding_pair, None
            )
            print(f"[Phone] 已将线上内容写入 {name} 的记忆")
        except Exception as e:
            print(f"[Phone] 写入记忆失败: {e}")
    
    # 3. 生成自己的发言
    response = generate_phone_browsing_reaction(persona, recent_posts, maze)
    
    # 4. 如果有发言，写入舆论库
    if response:
        post = post_online_opinion(persona, response, sim_folder)
        
        # 同时将自己的发言也写入记忆
        try:
            my_post_memory = f"{name}在网上发表了自己的看法：'{response}'"
            created = curr_time
            expiration = curr_time + datetime.timedelta(days=30)
            
            thought_embedding_pair = (my_post_memory, get_embedding(my_post_memory))
            
            persona.a_mem.add_thought(
                created, expiration, name, "posted_online", "opinion",
                my_post_memory, {"phone", "post", "opinion"}, 6,
                thought_embedding_pair, None
            )
        except:
            pass
        
        print(f"[Phone] {online_name} 发言完成")
    else:
        print(f"[Phone] {name} 选择不发言")
    
    # 标记已刷手机
    if not hasattr(persona.scratch, "phone_browse_times"):
        persona.scratch.phone_browse_times = []
    persona.scratch.phone_browse_times.append(curr_time.strftime("%H:%M"))
    
    print(f"[Phone] === {name} 刷手机结束 ===\n")
    
    return True

# ============================================================================
# 专家读取舆论库
# ============================================================================

def get_online_opinions_for_experts(since_hours=24, sim_folder=None, curr_time=None):
    """
    获取线上舆论供专家分析
    
    Args:
        since_hours: 获取多少小时内的帖子
        sim_folder: simulation文件夹路径
        curr_time: 当前时间
    
    Returns:
        str: 格式化的舆论内容
    """
    if curr_time is None:
        curr_time = datetime.datetime.now()
    
    since_time = curr_time - datetime.timedelta(hours=since_hours)
    
    posts = read_posts_since(since_time, sim_folder)
    
    if not posts:
        return "【网络舆情】过去24小时内没有网民发言。"
    
    result = f"【网络舆情汇总】过去{since_hours}小时内共有{len(posts)}条网民发言：\n\n"
    
    for post in posts:
        result += f"[{post['timestamp']}] {post['online_name']}: {post['content']}\n"
    
    return result

def format_posts_for_display(posts):
    """格式化帖子用于显示"""
    if not posts:
        return "暂无发言"
    
    lines = []
    for post in posts:
        time_str = post.get("timestamp", "未知时间")
        online_name = post.get("online_name", "匿名")
        content = post.get("content", "")
        lines.append(f"[{time_str}] {online_name}: {content}")
    
    return "\n".join(lines)

# ============================================================================
# 刷手机频率配置
# ============================================================================

PHONE_USAGE_CONFIG = {
    # 重度用户：3-4次/天
    "高建国": {"min_times": 3, "max_times": 4, "preferred_hours": [9, 14, 19, 23]},
    "韩小雪": {"min_times": 2, "max_times": 3, "preferred_hours": [7, 16, 21]},
    
    # 中度用户：1-2次/天
    "陈思远": {"min_times": 1, "max_times": 2, "preferred_hours": [10, 22]},
    "王丽华": {"min_times": 1, "max_times": 2, "preferred_hours": [12, 20]},
    "周小艺": {"min_times": 1, "max_times": 2, "preferred_hours": [15, 21]},
    "张国庆": {"min_times": 1, "max_times": 1, "preferred_hours": [20]},
    
    # 轻度用户：0-1次/天
    "林小雨": {"min_times": 0, "max_times": 1, "preferred_hours": [21]},
    "李大强": {"min_times": 0, "max_times": 1, "preferred_hours": [22]},
    
    # 几乎不用
    "刘小敏": {"min_times": 0, "max_times": 0, "preferred_hours": []},
}

def should_browse_phone(persona, current_hour):
    """
    判断当前是否应该刷手机
    
    基于任务描述判断 - LLM 会根据 daily_plan_req 中的刷手机习惯自然安排
    
    Args:
        persona: Persona实例
        current_hour: 当前小时（0-23）
    
    Returns:
        bool: 是否应该刷手机
    """
    # 检查当前任务描述是否包含刷手机相关关键词
    curr_action = getattr(persona.scratch, "act_description", "") or ""
    phone_keywords = ["刷手机", "玩手机", "看手机", "社交媒体", "刷微博", "刷抖音", 
                      "看新闻", "看评论", "browsing phone", "social media"]
    
    for keyword in phone_keywords:
        if keyword in curr_action:
            return True
    
    return False

def get_phone_usage_description(name):
    """获取人物的刷手机习惯描述（用于prompt）"""
    config = PHONE_USAGE_CONFIG.get(name, {})
    
    if config.get("max_times", 0) >= 3:
        return f"{name}是重度手机用户，经常刷社交媒体和评论区，每天会刷很多次手机。"
    elif config.get("max_times", 0) >= 2:
        return f"{name}偶尔会刷手机看看网上的讨论。"
    elif config.get("max_times", 0) >= 1:
        return f"{name}偶尔会看一下手机，但不太爱发言。"
    else:
        return f"{name}几乎不玩手机。"
