# 专家会议完整逻辑流程图

## 一、总体流程

```mermaid
flowchart TB
    subgraph 触发阶段["🕐 触发阶段 (23:00)"]
        A[模拟时间到达 23:00] --> B[reverie.py 检测触发条件]
        B --> C[创建 ExpertMeeting 对象]
        C --> D[启动后台线程运行会议]
        D --> E[前端时间继续流动]
    end

    subgraph 会议阶段["🎤 会议阶段"]
        F[主持人开场白] --> G[第1轮讨论]
        G --> H[第2轮讨论]
        H --> I[第3轮讨论 - 最终轮]
    end

    subgraph 结束阶段["✅ 结束阶段"]
        J[生成最终决策] --> K[提取平民版通报]
        K --> L[写入平民记忆]
        L --> M[触发专家反思]
        M --> N[会议完成]
    end

    E --> F
    I --> J
```

## 二、单轮讨论流程（第1-2轮）

```mermaid
flowchart LR
    subgraph 准备["准备"]
        A1[主持人决定发言顺序]
    end

    subgraph 引导["引导"]
        B1[主持人引导发言]
    end

    subgraph 发言["专家发言"]
        C1[公共卫生专家] --> C2[市场监管专家]
        C2 --> C3[教育局代表]
    end

    subgraph 总结["总结"]
        D1[主持人总结本轮]
        D2[对专家A意见]
        D3[对专家B意见]
        D4[对专家C意见]
    end

    A1 --> B1 --> C1
    C3 --> D1 --> D2 --> D3 --> D4
```

## 三、最终轮流程（第3轮）

```mermaid
flowchart LR
    subgraph 发言["专家发言"]
        A[公共卫生专家] --> B[市场监管专家]
        B --> C[教育局代表]
    end

    subgraph 最终总结["最终总结与决策"]
        D["## 一、本轮讨论要点"]
        E["## 二、全程会议回顾"]
        F["## 三、最终决策与行动建议"]
        G["## 四、责任分工"]
        H["## 五、结语"]
    end

    C --> D --> E --> F --> G --> H
```

## 四、专家发言信息检索流程

```mermaid
flowchart TB
    subgraph 输入["输入"]
        Q[议题/问题]
        T[会议时间 23:00]
    end

    subgraph 检索["信息检索 (24小时窗口)"]
        M1["📝 长期记忆<br/>昨天23:00 ~ 今天23:00"]
        M2["📚 案例知识库"]
        M3["📋 规则库条文"]
        M4["👥 公众舆论<br/>(平民对话摘要)"]
        M5["🌐 Tavily网络搜索"]
    end

    subgraph 生成["生成发言"]
        G1[构建Prompt]
        G2[调用LLM]
        G3[专家发言内容]
    end

    subgraph 保存["保存"]
        S1[保存reasoning到全局变量]
        S2[前端显示灰色小字]
    end

    Q --> M1 & M2 & M3 & M4 & M5
    T --> M1
    M1 & M2 & M3 & M4 & M5 --> G1 --> G2 --> G3
    G1 --> S1 --> S2
```

## 五、记忆写入流程

```mermaid
flowchart TB
    subgraph 会议中["会议进行中"]
        A[每轮总结] --> B[写入专家记忆<br/>write_round_summary_to_expert_memory]
        A --> C[写入主持人记忆<br/>write_meeting_to_moderator_memory]
    end

    subgraph 会议后["会议结束后"]
        D[最终决策] --> E[提取平民版通报<br/>extract_decision_for_civilians]
        E --> F[写入平民记忆<br/>broadcast_decision_to_civilians]
    end

    subgraph 反思["触发反思"]
        G[设置chat状态<br/>setup_meeting_chat_state]
        G --> H[下一时间步触发reflect]
    end

    B & C --> D
    F --> G
```

## 六、前端显示逻辑

```mermaid
flowchart TB
    subgraph 轮询["前端轮询"]
        A[每3秒检查 /check_expert_meeting/]
        A --> B{有触发文件?}
        B -->|是| C[显示弹窗]
        B -->|否| A
    end

    subgraph 显示["弹窗内容"]
        D[发言列表]
        E["灰色小字：思考依据<br/>📝记忆 📚案例 📋规则 👥舆论"]
        F[发言内容]
        G[状态指示器]
    end

    subgraph 类型["发言类型标签"]
        T1["【开场】"]
        T2["【引导】"]
        T3["【发言】"]
        T4["【总结与意见】"]
        T5["【🏁 最终总结与决策】"]
    end

    C --> D --> E --> F --> G
    D --> T1 & T2 & T3 & T4 & T5
```

## 七、关键函数调用链

```
reverie.py
│
├── 23:00 触发
│   └── threading.Thread(target=run_meeting)
│
└── ExpertMeeting(personas, topic, created_time)
    │
    ├── start_meeting()
    │   └── moderator_opening_speech()
    │
    ├── run_full_round_streaming() × 3轮
    │   ├── next_round()
    │   ├── moderator_introduce_expert()
    │   ├── expert_speak()
    │   │   └── get_expert_speech_function()
    │   │       ├── expert_meeting_speech()           # 公共卫生
    │   │       ├── market_supervision_expert_meeting_speech()  # 市场监管
    │   │       └── education_expert_meeting_speech() # 教育局
    │   │
    │   └── end_round(is_final_round)
    │       ├── 第1-2轮: moderator_round_summary()
    │       │           + moderator_give_targeted_advice()
    │       │
    │       └── 第3轮:   moderator_final_summary_and_decision()
    │                   (不再对专家提意见)
    │
    └── finalize_meeting()
        ├── setup_meeting_chat_state()  # 触发反思
        ├── extract_decision_for_civilians()  # 提取平民版
        └── broadcast_decision_to_civilians() # 写入平民记忆
```

## 八、时间线示意

```
Day 1                                    Day 2
──────────────────────────────────────────────────────────────
00:00  ...  10:55      ...      23:00                    23:00
        │              │         │                         │
        │              │         │                         │
        ▼              ▼         ▼                         ▼
   [收集平民对话]  [日常活动]  [专家会议]              [下次会议]
   [写入专家记忆]              │
                               ├── 主持人开场
                               ├── 第1轮讨论 + 总结
                               ├── 第2轮讨论 + 总结
                               ├── 第3轮讨论 + 最终决策
                               ├── 写入平民记忆
                               └── 触发反思
                                        │
                                        ▼
                               [记忆检索范围]
                               昨天23:00 ~ 今天23:00
```

## 九、核心文件清单

| 文件 | 功能 |
|-----|------|
| `expert_init.py` | 专家会议核心逻辑、发言生成、记忆写入 |
| `reverie.py` | 会议触发、后台线程运行 |
| `home.html` | 弹窗UI样式 |
| `main_script.html` | 前端轮询、发言渲染逻辑 |
| `views.py` | API接口 `/check_expert_meeting/` |

## 十、全局变量

| 变量 | 用途 |
|-----|------|
| `_last_expert_reasoning` | 保存最后一次发言的思考依据，供前端显示 |
| `_meeting_thread_running` | 标记会议线程是否在运行 |
| `meeting_triggered` | 标记今天是否已触发会议 |
