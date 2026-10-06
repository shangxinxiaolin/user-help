# 全链路串联与复盘

> 把前面每一块拼回一张完整的图：一条请求六站接力、两条走查、一份踩坑清单、一份选型指南。

## 一条请求的六站接力

目标系统入口（E 阶段尚未实现）：客户端 → Spring Boot entry Gateway/BFF → 内部 HTTP/SSE → Python 六站编排；业务工具 → gRPC → 同一 Spring Boot 的业务模块。普通业务不经过 Agent。Java 验证登录身份，Python 验证内部上下文并维护会话；Java 转发不持有业务事务，Python 不回调 Agent 入口。当前本地开发仍直接请求 Python。

```text
用户消息 → resolve_reference(指代消解) → classify_intent(意图识别)
  → route_by_intent 分流
      knowledge       → retrieve_knowledge → confidence_check → main_agent
      business        → main_agent
      refund_flow     → fetch_order → retrieve_policy → main_agent
      fallback_script → script_reply
      escalate        → complaint_reply
  → main_agent ⇄ agent_tools → log → 响应
```

暗线：会话上下文（LangGraph `State`）从第一站贯穿到最后，每站读它、写它。

## 两条请求走查

1. **正常 refund_flow**：「我早上买的这个还能退吗」→ 指代消解补全"蓝牙耳机" → 判退款退货 → 进子流程查订单（未发货）+ 强制检索政策 → Agent 判能退 → 正常回复。
2. **兜底进飞轮**：「跨店满减能叠积分券吗」→ 判商品咨询 → 强制检索但知识库没这条 → 置信度闸拦住 → 兜底话术 + 记入低置信度问题池 → 标准化查重 → 人工审核写回。

## 踩坑清单（8 条，见 SPEC 13.4）

| # | 坑 | 解法 |
|---|---|---|
| 1 | 关键词查表必漏召回 | RAG 换语义检索 |
| 2 | 向量单路漏 SKU/型号/券码 | BM25 + RRF + Rerank |
| 3 | 切分切歪救不回 | 结构感知切分 + 关键条款标记 |
| 4 | 扩召回在入库侧拆多份占满 Top-K | 检索侧 Query 扩写 |
| 5 | Agent 守不住硬约束 | Workflow 写死强制检索/取证/转人工 |
| 6 | 意图边界不清准确率上不去 | prompt 划清边界 |
| 7 | 光靠滑窗漏早期上下文 | 三层分层 |
| 8 | 数据质量决定微调成败 | 先搞数据 |

**规律**：越出在数据和流程上的坑越致命——模型再强，也补不回切分不对的一刀、标乱的一个标签，更救不回幻觉时的流程。

## 选型指南（10 项，见 SPEC 2.2）

LangChain（接 LLM/Prompt）→ LangGraph（编排）→ BGE-M3（嵌入）→ Milvus（向量+BM25）→ bge-reranker（精排）→ LLM+prompt（意图识别）→ LangGraph State（上下文）→ @tool + MCP（工具）→ Langfuse（可观测）→ RoBERTa-wwm-ext（微调）。

每一项只记两件事：**为什么选它、什么场景才真用得上**；涉及具体数值（准确率/召回率/延迟）一律等开发后用自己的评估集实测，不提前承诺。

## 小结

这组文档描述目标设计，不代表已经搭建。当前只有基础聊天、仓储和 checkpoint 封装，HTTP 仓储接线未完成；RAG、工具、意图、三层上下文、观测与飞轮待实现，微调后置。验收结果须另行记录。

## SPEC 落点

- 选型理由与触发场景：SPEC 2.2。
- 踩坑复盘清单：SPEC 13.4。
- 其余模块落点见各分册（01–09）。
