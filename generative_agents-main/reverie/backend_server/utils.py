# -*- coding: utf-8 -*-
# Utility configuration for the Reverie backend.
# 将 DeepSeek API Key 与使用者信息填入占位符即可。

# Copy and paste your DeepSeek API Key
deepseek_api_key = "sk-1425a2c9096645888105644b7db582d9"

# Put your name
key_owner = "lixuran"

maze_assets_loc = "../../../environment/frontend_server/static_dirs/assets"
# 环境资源指向 the_ville（当前项目资产在该目录）
env_matrix = f"{maze_assets_loc}/the_ville/matrix"
env_visuals = f"{maze_assets_loc}/the_ville/visuals"

fs_storage = "../../../environment/frontend_server/storage"
fs_temp_storage = "../../../environment/frontend_server/temp_storage"

collision_block_id = "32125"

# Verbose 控制
debug = True
