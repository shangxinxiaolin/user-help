# Workflow + Agent 混合架构

> 用 Workflow 搭确定性骨架（硬约束焊死在轨道上），把唯一需要临场判断的"怎么查数据"交给主力 Agent 用 ReAct 循环自己决定。

## 背景与问题

用户报手机号查物流，模型要"先查订单拿单号、再拿单号查物流"——两步工具调用，第二步依赖第一步的结果。这是纯 Workflow（写死流程）和裸 LLM（不给工具）都接不住的活。

## 设计

- **两个概念**：`Workflow` = 开发者写死流程、运行时严格照走；`Agent` = 把"下一步干嘛"交给模型运行时决定。差别在**控制权交给谁**。
- **六站接力**：

```text
resolve_reference → classify_intent → route_by_intent
  ├─ knowledge     → retrieve_knowledge → confidence_check → main_agent
  ├─ business      → main_agent
  ├─ refund_flow   → fetch_order → retrieve_policy → main_agent
  ├─ fallback_script → script_reply
  └─ escalate      → complaint_reply
  → main_agent ⇄ agent_tools → log
```

- **主力 Agent = ReAct 循环**：`Thought → Action → Observation`，每拿到一个 Observation 就重新想一次，直到信息够收敛。

```python
for _ in range(max_turns):
    ai_msg = await llm_with_tools.ainvoke(messages)
    if not ai_msg.tool_calls:
        return ai_msg
    for tc in ai_msg.tool_calls:
        messages.append(await tool.ainvoke(tc))
```

- **骨架归 Workflow，脑子归 Agent**：指代消解、意图识别、分流、证据闸走确定性路径；只有 `main_agent` 是临场判断。

## 选型理由

- **纯 Agent 三个致命伤**：①排查不可复现（两次跑路径不同）；②漏流程（忘检索、该拒答硬答）；③首句响应慢。
- **纯 Workflow 接不住组合多变**：业务数据每一步依赖上一步结果，每新增组合就加分支，代码爆炸。
- **LangGraph 编排**：流程要分流、汇合、循环，状态要贯穿，链式（`|`）拼不出来；图结构把每步做成节点、边挂条件，主力 Agent 只是其中一个节点，checkpoint 还能持久化中断恢复。

## 关键结论与坑

- **ReAct 精髓**："每拿到一个 Observation 就重新想一次"，不是提前规划整条路径。
- **Agent 是纯 LLM 的超集**：简单场景退化成一次调用（零成本），复杂场景才展开多轮。
- **`max_turns` 防钻牛角尖**：客服场景一轮最多两三步，封 6 步够用还留余量。
- **token 花销不该当停止条件**：它防的是烧钱和撑爆上下文，不是死循环；掐错位置会让用户看到半句"好的我来查一下"就没了下文。
- **Workflow 把硬约束变成"代码逻辑上绕不过去"**：知识类强制检索、退款取证、投诉转人工，写死在轨道里，模型没有"忘记"这一说。

## SPEC 落点

- Agent 工作流与节点职责：SPEC 第 5 节（与本文六站完全对应）。
- 当前实现：`app/graph/build.py` 仅有 `chat + log` 两节点，为 A 阶段中间态。
