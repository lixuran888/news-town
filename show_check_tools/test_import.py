#!/usr/bin/env python3
import sys
import os

# 测试导入专家位置监控模块
expert_path = os.path.join(os.getcwd(), 'seminar_expert', 'expert_system')
print(f"Expert path: {expert_path}")
print(f"Path exists: {os.path.exists(expert_path)}")

if os.path.exists(expert_path):
    files = os.listdir(expert_path)
    print(f"Files in directory: {files}")
    
    sys.path.append(expert_path)
    
    try:
        import expert_position_monitor
        print("✓ Import successful!")
        print(f"Module file: {expert_position_monitor.__file__}")
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("✗ Path does not exist")
