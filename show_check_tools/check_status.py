import os, sys
sys.stdout.reconfigure(encoding='utf-8')

storage = r'e:\generative_agents-main\environment\frontend_server\storage'
sims = [d for d in os.listdir(storage) if d.startswith('auto_run')]
sims.sort(reverse=True)

if not sims:
    print('没有模拟目录')
    exit()

print(f'最新模拟: {sims[0]}')

sim_dir = os.path.join(storage, sims[0])
movement_dir = os.path.join(sim_dir, 'movement')

if os.path.exists(movement_dir):
    files = os.listdir(movement_dir)
    print(f'Movement 文件数: {len(files)}')
    if files:
        nums = [int(f.split('.')[0]) for f in files if f.endswith('.json')]
        if nums:
            print(f'最新步数: {max(nums)}')
else:
    print('无 movement 目录')

# 检查 environment 文件
env_dir = os.path.join(sim_dir, 'environment')
if os.path.exists(env_dir):
    env_files = os.listdir(env_dir)
    print(f'Environment 文件数: {len(env_files)}')
else:
    print('无 environment 目录')
