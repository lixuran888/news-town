# 检查当前世界线信息
import os, json, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'

sims = sorted([d for d in os.listdir(storage) if d.startswith('auto_run')], reverse=True)

if sims:
    latest = sims[0]
    meta_path = os.path.join(storage, latest, 'reverie', 'meta.json')
    if os.path.exists(meta_path):
        with open(meta_path, encoding='utf-8') as f:
            meta = json.load(f)
        print(f'最新世界线: {latest}')
        print(f'当前时间: {meta.get("curr_time", "unknown")}')
        print(f'Fork from: {meta.get("fork_sim_code", "unknown")}')
        print(f'Step: {meta.get("step", "unknown")}')
        
        # 检查是 08:00 还是 20:00 开始
        curr_time = meta.get("curr_time", "")
        if "08:" in curr_time[:20]:
            print('\n⚠️ 这是旧世界线（08:00 开始）')
            print('需要重新 fork 才能应用 20:00 开始时间')
        elif "20:" in curr_time[:20]:
            print('\n✅ 这是新世界线（20:00 开始）')
else:
    print('没有找到 auto_run 世界线')
