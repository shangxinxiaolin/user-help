# Workflow + Agent 混合架构

> 用 Workflow 搭确定性骨架（硬约束焊死在轨道上），把唯一需要临场判断的"怎么查数据"交给主力 Agent 用 ReAct 循环自己决定。

## 背景与问题

先查订单再查物流是固定两步依赖，Workflow 完全能实现；Agent 用于根据运行时信息动态选择工具组合和澄清参数。手机号查单仅为假设场景，当前 Java 契约不支持。

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
    messages.append(ai_msg)  # 保留携带 tool_calls 的 assistant 消息
    for tc in ai_msg.tool_calls:
        messages.append(await execute_registered_tool(tc))  # 返回匹配 tool_call_id 的 ToolMessage
```

- **骨架归 Workflow**：编排顺序与条件边由代码固定，指代与意图等 LLM 判断仍可能变化；固定路径不等于结果确定性。

## 选型理由

上述循环仅为伪代码；execute_registered_tool 需实现注册查找、参数校验、身份注入、超时与 ToolMessage 封装，到步数上限需有明确兜底。

- **纯 Agent 三个致命伤**：①排查不可复现（两次跑路径不同）；②漏流程（忘检索、该拒答硬答）；③首句响应慢。
- **纯 Workflow 接不住组合多变**：业务数据每一步依赖上一步结果，每新增组合就加分支，代码爆炸。
- **LangGraph 编排**：流程要分流、汇合、循环，状态要贯穿，链式（`|`）拼不出来；图结构把每步做成节点、边挂条件，主力 Agent 只是其中一个节点，checkpoint 还能持久化中断恢复。

## 关键结论与坑

- **ReAct 精髓**："每拿到一个 Observation 就重新想一次"，不是提前规划整条路径。
- **简单场景退化成一次模型调用**：无额外工具循环开销，但仍有模型费用与延迟。
- **`max_turns` 防钻牛角尖**：客服场景一轮最多两三步，封 6 步够用还留余量。
- **token 花销不该当停止条件**：它防的是烧钱和撑爆上下文，不是死循环；掐错位置会让用户看到半句"好的我来查一下"就没了下文。
- **Workflow 把硬约束变成"代码逻辑上绕不过去"**：知识类强制检索、退款取证、投诉转人工，写死在轨道里，模型没有"忘记"这一说。

## SPEC 落点

- 工作流见总规格 1.3 和 Python 服务规格第 5 节；实施顺序见总规格 12.6。
- 当前实现：`app/graph/build.py` 仅有 `chat + log` 两节点，为 A 阶段中间态。
