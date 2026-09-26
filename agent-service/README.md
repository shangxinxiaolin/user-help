# Python Agent Service

灵犀客服的 Python Agent Service 目录。

## 当前状态

该目录已经纳入项目，但 Python 原项目尚未迁移进来。当前仓库优先完成 Java Business Service，并稳定 Python 与 Java 之间的 Protobuf 契约。

详细设计见：[Python Agent Service 规格书](docs/PYTHON_AGENT_SERVICE_SPEC.md)。

## 计划结构

```text
agent-service/
├── app/
│   ├── api/             # FastAPI 接口
│   ├── graph/           # LangGraph 工作流
│   ├── core/            # LLM、意图、检索、上下文管理
│   ├── tools/           # LangChain Tools
│   ├── grpc_client/     # Java Business Service 客户端
│   └── kb/              # 知识库能力
├── tests/
├── pyproject.toml
└── README.md
```

## 后续接入顺序

1. 迁移原 Python Agent 项目。
2. 根据 `../business-service/src/main/proto/business_service.proto` 生成 Python gRPC Stub。
3. 先改造 `query_order` 工具。
4. 再改造物流、售后、退款和工单工具。
5. 完成 Python Agent 到 Java Business Service 的端到端联调。
