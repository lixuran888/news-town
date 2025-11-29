/**
 * 专家会议触发检测器
 * 定期检查触发文件，当所有专家到达指定位置时显示专家对话界面
 */

class ExpertTriggerDetector {
    constructor() {
        this.checkInterval = 3000; // 3秒检查一次
        this.triggerFile = '/expert_meeting_trigger.flag';
        this.conversationShown = false;
        this.intervalId = null;
        
        this.startDetection();
    }
    
    startDetection() {
        console.log('[ExpertTrigger] 开始检测专家会议触发');
        
        this.intervalId = setInterval(() => {
            this.checkTriggerFile();
        }, this.checkInterval);
    }
    
    stopDetection() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
    
    async checkTriggerFile() {
        // 检查当前模拟时间，只在23:00后才检测
        const timeElement = document.querySelector('#curr_time');
        if (timeElement) {
            const timeText = timeElement.textContent;
            if (timeText && timeText.includes(':')) {
                const hour = parseInt(timeText.split(':')[0]);
                if (hour < 23) {
                    // console.log('[ExpertTrigger] 未到检测时间，跳过');
                    return;
                }
            }
        }
        
        try {
            const response = await fetch(this.triggerFile);
            
            if (response.ok) {
                const triggerData = await response.json();
                console.log('[ExpertTrigger] 检测到触发文件:', triggerData);
                
                if (triggerData.action === 'show_expert_conversation' && !this.conversationShown) {
                    this.showExpertConversation(triggerData);
                }
            }
        } catch (error) {
            // 文件不存在或其他错误，继续检测
            // console.log('[ExpertTrigger] 触发文件未就绪');
        }
    }
    
    showExpertConversation(triggerData) {
        console.log('[ExpertTrigger] 显示专家对话界面');
        
        // 创建专家对话界面
        if (!document.getElementById('expert-conversation-frame')) {
            const iframe = document.createElement('iframe');
            iframe.id = 'expert-conversation-frame';
            iframe.src = '/seminar_expert/expert_system/1.expert_agent_conversation.html';
            iframe.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                width: 450px;
                height: 600px;
                border: none;
                border-radius: 16px;
                box-shadow: 0 25px 60px rgba(0,0,0,0.4);
                z-index: 9999;
                background: rgba(15, 23, 42, 0.95);
                backdrop-filter: blur(10px);
                opacity: 0;
                transform: translateY(-20px);
                transition: all 0.5s ease;
            `;
            
            document.body.appendChild(iframe);
            
            // 动画显示
            setTimeout(() => {
                iframe.style.opacity = '1';
                iframe.style.transform = 'translateY(0)';
            }, 100);
            
            // 添加关闭按钮
            this.addCloseButton(iframe);
            
            this.conversationShown = true;
            this.stopDetection(); // 停止检测
            
            console.log('[ExpertTrigger] 专家对话界面已显示');
        }
    }
    
    addCloseButton(iframe) {
        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '×';
        closeBtn.style.cssText = `
            position: fixed;
            top: 25px;
            right: 25px;
            width: 32px;
            height: 32px;
            border: none;
            border-radius: 50%;
            background: rgba(239, 68, 68, 0.2);
            color: #fecaca;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            z-index: 10000;
            transition: background 0.2s ease;
        `;
        
        closeBtn.addEventListener('mouseenter', () => {
            closeBtn.style.background = 'rgba(239, 68, 68, 0.4)';
        });
        
        closeBtn.addEventListener('mouseleave', () => {
            closeBtn.style.background = 'rgba(239, 68, 68, 0.2)';
        });
        
        closeBtn.addEventListener('click', () => {
            iframe.style.opacity = '0';
            iframe.style.transform = 'translateY(-20px)';
            closeBtn.style.opacity = '0';
            
            setTimeout(() => {
                iframe.remove();
                closeBtn.remove();
            }, 500);
        });
        
        document.body.appendChild(closeBtn);
    }
}

// 自动启动检测器
let expertTriggerDetector = null;

// 等待页面加载完成
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        expertTriggerDetector = new ExpertTriggerDetector();
    });
} else {
    expertTriggerDetector = new ExpertTriggerDetector();
}

// 导出供其他脚本使用
window.ExpertTriggerDetector = ExpertTriggerDetector;
