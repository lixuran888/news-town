# -*- coding: utf-8 -*-
"""
Quick test for expert meeting popup (non-interactive)
Creates trigger file and tests API
"""

import json
import os
from datetime import datetime
from pathlib import Path

print("=" * 60)
print("[TEST] Expert Meeting Popup Quick Test")
print("=" * 60)

# Trigger file path
trigger_path = Path(__file__).parent / "environment" / "frontend_server" / "temp_storage" / "expert_meeting_trigger.json"
print(f"\nTrigger file path: {trigger_path}")

# 确保目录存在
trigger_path.parent.mkdir(parents=True, exist_ok=True)

# Step 1: Remove old file
if trigger_path.exists():
    os.remove(trigger_path)
    print("[OK] Old trigger file removed")

# Step 2: Create new trigger file
trigger_data = {
    "timestamp": datetime.now().isoformat(),
    "action": "show_expert_conversation",
    "test_mode": True
}

with open(trigger_path, 'w', encoding='utf-8') as f:
    json.dump(trigger_data, f, ensure_ascii=False, indent=2)

print(f"[OK] Trigger file created!")
print(f"    Content: {json.dumps(trigger_data, ensure_ascii=False)}")

# Step 3: Test API
print("\n--- Testing API endpoint ---")
try:
    import urllib.request
    url = "http://127.0.0.1:8000/check_expert_meeting/"
    
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(f"[API] Response: {json.dumps(data, ensure_ascii=False)}")
        
        if data.get('triggered'):
            print("\n" + "=" * 60)
            print("[SUCCESS] Test passed!")
            print("   Open browser: http://127.0.0.1:8000/simulator_home")
            print("   Check if popup appears (within ~3 seconds)")
            print("=" * 60)
        else:
            print("\n[WARN] API returned triggered=false, check file path")
            
except urllib.error.URLError as e:
    print(f"\n[ERROR] API request failed: {e}")
    print("   Make sure Django server is running:")
    print("   cd environment/frontend_server")
    print("   python manage.py runserver")
except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")

print("\nTip: To reset test, delete trigger file and refresh browser")
