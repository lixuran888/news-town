"""
专家位置监控系统
从23:00开始检测所有专家位置，当全部到达指定位置时触发专家对话界面
"""

import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime

# 专家列表
EXPERTS = [
    "Public Health Expert",
    "Market Supervision Expert",
    "Education Bureau Representative",
    "Meeting Moderator"
]
# 会议地点：Dorm common room 的可达中心位置
MEETING_CENTER = (120, 49)  # 修正为可达坐标
POSITION_TOLERANCE = 5  # 位置容差（同一区域内即可）

# 监控配置
MONITOR_START_TIME = "23:00"  # 开始监控时间
CHECK_INTERVAL = 5  # 检查间隔(秒)
# 使用绝对路径，确保 Django 和 Reverie 都能访问同一文件
TRIGGER_FILE = Path(__file__).parent.parent.parent / "environment" / "frontend_server" / "expert_meeting_trigger.flag"

class ExpertPositionMonitor:
    def __init__(self, simulation_dir):
        self.simulation_dir = Path(simulation_dir)
        self.monitoring = False
        self.experts_arrived = set()
        self.trigger_sent = False
        
    def get_latest_simulation_dir(self):
        """获取最新的模拟目录"""
        storage_path = Path("environment/frontend_server/storage")
        if not storage_path.exists():
            return None
            
        # 查找最新的模拟目录
        sim_dirs = [d for d in storage_path.iterdir() 
                   if d.is_dir() and d.name.startswith("base_the_ville")]
        
        if not sim_dirs:
            return None
            
        # 返回最新修改的目录
        latest_dir = max(sim_dirs, key=lambda x: x.stat().st_mtime)
        return latest_dir
    
    def get_persona_position_from_movement(self, persona_name, step):
        """从movement文件获取角色当前位置"""
        try:
            movement_file = self.simulation_dir / "movement" / f"{step}.json"
            
            if not movement_file.exists():
                return None
                
            with open(movement_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 获取角色位置
            persona_data = data.get("persona", {}).get(persona_name)
            if persona_data and "movement" in persona_data:
                movement = persona_data["movement"]
                if len(movement) >= 2:
                    return (movement[0], movement[1])
                
        except Exception as e:
            print(f"[Monitor] 从movement文件获取 {persona_name} 位置失败: {e}")
            
        return None
    
    def is_at_target_position(self, position, expert_name=None):
        """检查是否到达会议地点（Dorm common room 区域）"""
        if not position:
            return False
        
        x, y = position
        target_x, target_y = MEETING_CENTER
        
        # 检查是否在会议地点附近
        return (abs(x - target_x) <= POSITION_TOLERANCE and 
                abs(y - target_y) <= POSITION_TOLERANCE)
    
    def get_current_simulation_time(self):
        """获取当前模拟时间"""
        try:
            return datetime.now().strftime("%H:%M")
        except:
            return "00:00"
    
    def check_all_experts_arrived(self, current_step):
        """检查所有专家是否都到达各自的目标位置"""
        arrived_count = 0
        
        for expert_name in EXPERTS:
            position = self.get_persona_position_from_movement(expert_name, current_step)
            target = EXPERT_TARGETS.get(expert_name, (139, 50))
            
            if self.is_at_target_position(position, expert_name):
                if expert_name not in self.experts_arrived:
                    self.experts_arrived.add(expert_name)
                    print(f"[Monitor] ✓ {expert_name} 已到达目标位置 {position} (目标: {target})")
                arrived_count += 1
            else:
                if position:
                    print(f"[Monitor] {expert_name} 当前位置: {position}, 目标: {target}")
                else:
                    print(f"[Monitor] {expert_name} 位置未知")
        
        return arrived_count == len(EXPERTS)
    
    def trigger_expert_meeting(self):
        """触发专家会议界面"""
        if self.trigger_sent:
            return
            
        print(f"\n[Monitor] 🎉 所有专家已到达目标位置！触发专家会议界面...")
        
        # 创建触发文件
        trigger_path = Path(TRIGGER_FILE)
        trigger_data = {
            "timestamp": datetime.now().isoformat(),
            "experts_arrived": list(self.experts_arrived),
            "target_positions": {k: list(v) for k, v in EXPERT_TARGETS.items()},
            "action": "show_expert_conversation"
        }
        
        with open(trigger_path, 'w', encoding='utf-8') as f:
            json.dump(trigger_data, f, ensure_ascii=False, indent=2)
        
        # 在前端显示专家对话界面
        self.show_expert_conversation_ui()
        
        self.trigger_sent = True
        print(f"[Monitor] 触发文件已创建: {trigger_path}")
    
    def show_expert_conversation_ui(self):
        """在界面右上角显示专家对话"""
        try:
            # 方法1: 通过JavaScript注入
            js_code = """
            // 创建专家对话界面
            if (!document.getElementById('expert-conversation-frame')) {
                const iframe = document.createElement('iframe');
                iframe.id = 'expert-conversation-frame';
                iframe.src = '1.expert_agent_conversation.html';
                iframe.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    width: 450px;
                    height: 600px;
                    border: none;
                    border-radius: 16px;
                    box-shadow: 0 25px 60px rgba(0,0,0,0.3);
                    z-index: 9999;
                    background: rgba(15, 23, 42, 0.95);
                `;
                document.body.appendChild(iframe);
                console.log('[ExpertMonitor] 专家对话界面已显示');
            }
            """
            
            # 写入JavaScript文件供前端调用
            js_file = Path("show_expert_conversation.js")
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write(js_code)
                
            print(f"[Monitor] JavaScript触发文件已创建: {js_file}")
            
        except Exception as e:
            print(f"[Monitor] 显示专家对话界面失败: {e}")
    
    # 不再需要独立的监控循环，直接在reverie.py主循环中检查
    
    def start_monitoring(self):
        """启动监控（简化版，不再需要独立线程）"""
        self.monitoring = True
        print(f"[Monitor] 专家位置监控已启动（集成到主循环）")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        print(f"[Monitor] 专家位置监控已停止")


def main():
    """主函数 - 可独立运行"""
    # 自动检测最新模拟目录
    monitor = ExpertPositionMonitor(None)
    latest_sim = monitor.get_latest_simulation_dir()
    
    if not latest_sim:
        print("[Monitor] 未找到模拟目录")
        return
        
    print(f"[Monitor] 使用模拟目录: {latest_sim}")
    monitor.simulation_dir = latest_sim
    
    try:
        monitor.start_monitoring()
        monitor.monitor_loop()  # 阻塞运行
    except KeyboardInterrupt:
        monitor.stop_monitoring()


if __name__ == "__main__":
    main()
