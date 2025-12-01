
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
            