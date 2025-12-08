# -*- coding: utf-8 -*-
# Utility configuration for the Reverie backend.
# 将 DeepSeek API Key 与使用者信息填入占位符即可。

# ============================================================================
# LLM API 配置 - 支持本地模型和云端 API
# ============================================================================

# 使用模式: "local" 或 "cloud"
# - "local": 使用本地模型（如 Ollama、vLLM 等）
# - "cloud": 使用云端 API（DeepSeek）
# 注意：如果 temp_storage/start_time_config.json 中有配置，会优先使用配置文件中的设置
USE_LOCAL_MODEL = False  # 默认值：关闭本地模型，使用云端API。如果配置文件中有设置会被覆盖

# 本地模型配置（当 USE_LOCAL_MODEL = True 时生效）
LOCAL_API_BASE = "http://localhost:11434/v1"  # Ollama 默认地址，如果是其他服务请修改
LOCAL_MODEL_NAME = "deepseek-R1:8b"  # 默认值，如果配置文件中有设置会被覆盖
LOCAL_API_KEY = "ollama"  # 本地 API 通常不需要真实 key，但有些服务需要，可以设为 "ollama" 或留空

# 云端 API 配置（当 USE_LOCAL_MODEL = False 时生效）
deepseek_api_key = "sk-1425a2c9096645888105644b7db582d9"
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL_NAME = "deepseek-chat"

# 先定义路径变量，以便在读取配置时使用
maze_assets_loc = "../../../environment/frontend_server/static_dirs/assets"
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"
fs_storage = "../../../environment/frontend_server/storage"
fs_temp_storage = "../../../environment/frontend_server/temp_storage"

# 从配置文件读取模型设置（如果存在）
try:
    import sys
    import os
    from pathlib import Path
    # 使用 fs_temp_storage 相对路径构建配置文件路径
    current_file = Path(__file__).resolve()
    # utils.py 在: generative_agents-main/reverie/backend_server/utils.py
    # temp_storage 在: environment/frontend_server/temp_storage
    # 从 backend_server 向上3级到项目根目录
    backend_server_dir = current_file.parent
    project_root = backend_server_dir.parent.parent.parent
    config_path = project_root / "environment" / "frontend_server" / "temp_storage" / "start_time_config.json"
    
    if config_path.exists():
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 读取配置
        if "use_local_model" in config_data:
            USE_LOCAL_MODEL = bool(config_data["use_local_model"])
        if "local_model_name" in config_data and config_data["local_model_name"]:
            LOCAL_MODEL_NAME = str(config_data["local_model_name"])
        
        # 明确的终端日志输出
        print("=" * 60)
        print(f"[LLM 配置] 📁 配置文件路径: {config_path}")
        print(f"[LLM 配置] 📋 读取到的配置: use_local_model={config_data.get('use_local_model')}, local_model_name={config_data.get('local_model_name')}")
        if USE_LOCAL_MODEL:
            print("[LLM 配置] ✅ 已启用本地模型模式")
            print(f"[LLM 配置] 模型名称: {LOCAL_MODEL_NAME}")
            print(f"[LLM 配置] API地址: {LOCAL_API_BASE}")
        else:
            print("[LLM 配置] ✅ 已启用云端API模式")
            print(f"[LLM 配置] 使用云端API: {DEEPSEEK_API_BASE}")
        print("=" * 60)
    else:
        # 配置文件不存在，使用默认值（云端API）
        print("=" * 60)
        print("[LLM 配置] ⚠️  未找到配置文件，使用默认设置")
        print(f"[LLM 配置] 🔍 尝试的路径: {config_path}")
        print("[LLM 配置] ✅ 默认使用云端API模式")
        print(f"[LLM 配置] API地址: {DEEPSEEK_API_BASE}")
        print("=" * 60)
except Exception as e:
    import traceback
    print("=" * 60)
    print(f"[LLM 配置] ❌ 读取模型配置失败: {e}")
    print(f"[LLM 配置] 错误详情: {traceback.format_exc()}")
    print("[LLM 配置] ✅ 使用默认设置：云端API模式")
    print(f"[LLM 配置] API地址: {DEEPSEEK_API_BASE}")
    print("=" * 60)

# API 超时配置（秒）- 本地模型可能较慢，可以设置更长
LLM_TIMEOUT = 60  # 本地模型建议60秒，云端API可以设置30秒

# Tavily API Key for web search (专家联网搜索)
tavily_api_key = "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"  # 请填入你的 Tavily API Key

# Put your name
key_owner = "lixuran"

# 环境资源指向 the_ville（当前项目资产在该目录）
# 注意：这些变量在上面已经定义，这里只是注释说明

collision_block_id = "32125"

# Verbose 控制
debug = True
