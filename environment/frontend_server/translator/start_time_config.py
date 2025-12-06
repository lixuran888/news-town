"""
独立的开始时间配置文件
使用独立的 JSON 文件存储开始时间，不依赖 base_the_ville_clean 的 meta.json
"""
import os
import json
import datetime
from pathlib import Path

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "temp_storage" / "start_time_config.json"

def get_config_path():
    """获取配置文件路径"""
    return CONFIG_FILE

def load_start_time():
    """
    读取开始时间配置
    返回: (start_date, curr_time) 或 (None, None)
    """
    if not CONFIG_FILE.exists():
        return None, None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        start_date = data.get("start_date")
        curr_time = data.get("curr_time")
        if start_date and curr_time:
            return start_date, curr_time
    except Exception as e:
        print(f"[start_time_config] 读取配置失败: {e}")
    
    return None, None

def save_start_time(start_date, curr_time):
    """
    保存开始时间配置
    start_date: "February 13, 2023" 格式
    curr_time: "February 13, 2023, 17:00:00" 格式
    """
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "start_date": start_date,
            "curr_time": curr_time,
            "updated_at": datetime.datetime.now().isoformat()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[start_time_config] 已保存开始时间: {start_date} / {curr_time}")
        return True
    except Exception as e:
        print(f"[start_time_config] 保存配置失败: {e}")
        return False

def get_default_time():
    """获取默认时间（从 base meta.json 读取，如果不存在则返回默认值）"""
    base_meta_path = Path(__file__).parent.parent / "storage" / "base_the_ville_clean" / "reverie" / "meta.json"
    if base_meta_path.exists():
        try:
            with open(base_meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            return meta.get("start_date", "February 13, 2023"), meta.get("curr_time", "February 13, 2023, 00:00:00")
        except:
            pass
    return "February 13, 2023", "February 13, 2023, 00:00:00"

