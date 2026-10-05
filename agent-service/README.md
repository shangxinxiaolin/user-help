# Python Agent Service

灵犀客服的 Python Agent Service 目录。

## 当前状态

Python Agent Service 按对话编排、知识检索和工具调用等职责逐步实现。目前已完成基础对话、Graph 消息状态、MySQL 会话/消息模型及仓储；业务工具部分后续通过 gRPC 调用 Java Business Service。

详细设计见：[Python Agent Service 规格书](docs/PYTHON_AGENT_SERVICE_SPEC.md)。

## 计划结构

```text
agent-service/
├── app/
│   ├── api/             # FastAPI 接口
│   ├── graph/           # LangGraph 状态、运行时、路由和节点包
│   ├── core/            # LLM、意图、检索、上下文管理
│   ├── tools/           # LangChain Tools
│   ├── grpc_client/     # Java Business Service 客户端
│   └── kb/              # 知识库能力
├── tests/
│   ├── api/
│   ├── core/
│   ├── graph/
│   ├── schemas/
│   └── fakes.py
├── pyproject.toml
└── README.md
```

## 后续接入顺序

按能力分阶段推进，每阶段完成测试与确认后再进入下一阶段：

1. **A 基础接线**：FastAPI 入口、会话仓储、LangGraph Checkpointer（已完成基础对话、会话/消息 ORM 与仓储）。
2. **B 只读业务链**：根据 `../business-service/src/main/proto/business_service.proto` 生成 gRPC Stub，`query_order` 改为调用 Java `OrderService`。
3. 依次重新实现物流、售后、退款和工单工具。
4. **D 政策依据与评测**：小范围政策 RAG、引用与低置信度处理。
5. 每个阶段完成后测试、讲解并等待确认，再进入下一阶段。

各模块设计与选型理由见 [`docs/design/`](docs/design/)（01–10 篇）。
