"""
测试专家位置监控和触发系统
"""

import json
import sys
import time
from pathlib import Path
# 确保可以导入seminar_expert目录下的模块
sys.path.append(str(Path(__file__).parent.parent / "seminar_expert" / "expert_system"))
from expert_position_monitor import ExpertPositionMonitor

def test_trigger_system():
    """测试专家触发系统"""
    print("=== 专家位置监控系统测试 ===\n")
    
    # 1. 创建监控器实例
    print("1. 创建监控器...")
    monitor = ExpertPositionMonitor("test_simulation")
    
    # 2. 创建测试用的movement文件
    print("2. 创建测试movement文件...")
    test_movement_dir = Path("test_simulation/movement")
    test_movement_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建测试movement数据 - 专家逐步移动到目标位置
    test_steps = [
        # Step 0: 专家在初始位置
        {
            "persona": {
                "Education Bureau Representative": {"movement": [100, 30]},
                "Meeting Moderator": {"movement": [110, 40]},
                "Public Health Expert": {"movement": [120, 35]},
                "Market Supervision Expert": {"movement": [130, 45]}
            },
            "meta": {"curr_time": "February 13, 2023, 23:00:00"}
        },
        # Step 1: 专家接近目标位置
        {
            "persona": {
                "Education Bureau Representative": {"movement": [142, 48]},
                "Meeting Moderator": {"movement": [144, 52]},
                "Public Health Expert": {"movement": [146, 49]},
                "Market Supervision Expert": {"movement": [143, 51]}
            },
            "meta": {"curr_time": "February 13, 2023, 23:01:00"}
        },
        # Step 2: 所有专家到达目标位置
        {
            "persona": {
                "Education Bureau Representative": {"movement": [145, 50]},
                "Meeting Moderator": {"movement": [145, 50]},
                "Public Health Expert": {"movement": [145, 50]},
                "Market Supervision Expert": {"movement": [145, 50]}
            },
            "meta": {"curr_time": "February 13, 2023, 23:02:00"}
        }
    ]
    
    # 写入测试movement文件
    for step, data in enumerate(test_steps):
        movement_file = test_movement_dir / f"{step}.json"
        with open(movement_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # 3. 测试位置检测
    print("3. 测试专家位置检测...")
    experts = [
        "Education Bureau Representative",
        "Meeting Moderator", 
        "Public Health Expert",
        "Market Supervision Expert"
    ]
    
    for step in range(len(test_steps)):
        print(f"\n   Step {step}:")
        arrived_count = 0
        
        for expert in experts:
            position = monitor.get_persona_position_from_movement(expert, step)
            is_arrived = monitor.is_at_target_position(position)
            
            if is_arrived:
                arrived_count += 1
                status = "✓"
            else:
                status = "○"
                
            print(f"     {status} {expert}: {position}")
        
        print(f"     已到达: {arrived_count}/{len(experts)}")
        
        if arrived_count == len(experts):
            print("     🎉 所有专家已到达目标位置！")
            
            # 4. 触发专家会议
            print("\n4. 触发专家会议...")
            for expert in experts:
                monitor.experts_arrived.add(expert)
            monitor.trigger_expert_meeting()
            break
    
    # 5. 检查触发文件
    print("\n5. 检查触发文件...")
    trigger_file = Path("expert_meeting_trigger.flag")
    
    if trigger_file.exists():
        print("   ✓ 触发文件已创建")
        
        with open(trigger_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("   触发文件内容:")
        print(f"   - 时间戳: {data.get('timestamp')}")
        print(f"   - 已到达专家: {data.get('experts_arrived')}")
        print(f"   - 目标位置: {data.get('target_position')}")
        print(f"   - 动作: {data.get('action')}")
        
    else:
        print("   ✗ 触发文件未找到")
    
    # 6. 检查JavaScript文件
    print("\n6. 检查JavaScript触发文件...")
    js_file = Path("show_expert_conversation.js")
    
    if js_file.exists():
        print("   ✓ JavaScript触发文件已创建")
        
        with open(js_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "expert-conversation-frame" in content:
            print("   ✓ JavaScript包含正确的界面创建代码")
        else:
            print("   ✗ JavaScript内容不正确")
    else:
        print("   ✗ JavaScript文件未找到")
    
    print("\n=== 测试完成 ===")
    
    # 清理测试文件
    import shutil
    cleanup_files = [trigger_file, js_file]
    cleanup_dirs = [Path("test_simulation")]
    
    for file_path in cleanup_files:
        if file_path.exists():
            file_path.unlink()
            print(f"已清理文件: {file_path}")
    
    for dir_path in cleanup_dirs:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"已清理目录: {dir_path}")

def test_position_detection():
    """测试位置检测逻辑"""
    print("\n=== 位置检测测试 ===\n")
    
    monitor = ExpertPositionMonitor("test")
    
    # 测试用例
    test_cases = [
        ((145, 50), True, "目标位置"),
        ((143, 48), True, "容差范围内"),
        ((148, 53), True, "容差范围内"),
        ((140, 45), False, "超出容差"),
        ((150, 55), False, "超出容差"),
        (None, False, "空位置"),
    ]
    
    for position, expected, description in test_cases:
        result = monitor.is_at_target_position(position)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}: {position} -> {result}")
    
    print("\n目标位置: (145, 50), 容差: ±3")

if __name__ == "__main__":
    test_position_detection()
    test_trigger_system()
