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

1. **A 基础接线（尚未验收）**：基础对话、会话/消息 ORM、仓储与 checkpoint 封装已有代码；HTTP 入口仍未注入仓储，需通过 FastAPI Depends 接通归属校验和消息落库，再验收重启恢复。
2. **B 只读业务链**：根据 `../business-service/src/main/proto/business_service.proto` 生成 gRPC Stub，新增 `query_order` 工具并调用 Java `OrderService`；当前尚无订单工具。
3. 依总规格 12.6 推进路由、上下文、RAG、观测、飞轮与评测；物流/售后工具按业务需求逐项扩展。
4. **C 可靠退款**：经确认后实现确认流程、Java 持久化幂等与状态机；工单按相同写操作边界扩展。
5. 每个阶段完成后测试、讲解并等待确认，再进入下一阶段。

各模块设计与选型理由见 [`docs/design/`](docs/design/)（01–10 篇）。

实际运行使用真实模型 API，确定性测试使用替身；RAG 目标采用支持所需 BM25/混合检索能力的 Milvus Standalone，Lite 兼容性需另行验证。飞轮采用批处理与完整审核接口；微调暂不实施。完整实施顺序以总规格 12.6 为准。
