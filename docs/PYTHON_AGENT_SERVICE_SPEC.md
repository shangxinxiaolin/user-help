# 灵犀客服 Python Agent Service 规格书

版本：v1.0  
状态：迁移实施规格  
更新时间：2026-09-27

## 1. 文档目的

本文档定义灵犀客服 Python Agent Service 的职责、目录结构、运行方式、Agent 工作流、工具迁移方案，以及与 Java Business Service 的 gRPC 对接契约。

原始 Python 项目位于：

```text
D:\智能客服\MEWHELP python
```

目标迁移目录为：

```text
D:\mewhelp-user-help\agent-service
```

当前 `agent-service/` 仅包含占位说明，原 Python 项目尚未迁移。本文档是后续迁移和联调的依据，不代表 Python 服务当前已经完成。

## 2. 服务定位

Python Agent Service 是系统的对话编排层，负责理解用户问题、组织上下文、选择工具、检索知识并生成回答。

### 2.1 Python Agent Service 负责

- FastAPI HTTP 接口
- SSE 流式聊天
- LangGraph 工作流
- LangChain 消息、Prompt 和 Tool
- 意图分类和指代消解
- FAQ 和知识库检索
- 证据置信度判断
- ReAct 工具调用循环
- 退款和工单的用户确认流程
- 对话上下文、摘要和 Checkpoint
- 工具调用审计和 Agent 可观测性
- 调用 Java Business Service 的 gRPC Client

### 2.2 Python Agent Service 不负责

- 订单数据的最终归属和业务规则
- 物流、售后、退款和工单的核心业务执行
- 订单归属的最终安全校验
- 退款和工单的真正写操作
- Java Business DB
- Java 服务内部的 Mock Mapper 或 MyBatis

调用关系：

```text
用户
  ↓ HTTP / SSE
Python Agent Service
  ├─ 意图识别
  ├─ LangGraph 编排
  ├─ LangChain Tool
  ├─ 知识检索
  └─ gRPC Client
       ↓
Java Business Service
  ├─ 订单
  ├─ 物流
  ├─ 售后
  ├─ 退款
  └─ 工单
```

## 3. 原项目现状

原项目使用 Python 3.12+，主要依赖如下：

| 能力 | 技术 |
|---|---|
| HTTP | FastAPI + Uvicorn |
| Agent 工作流 | LangGraph |
| LLM 和 Tool | LangChain + OpenAI SDK |
| 数据库 | SQLAlchemy asyncio + MySQL |
| 向量库 | Milvus |
| MCP | mcp + langchain-mcp-adapters |
| 可观测性 | Langfuse |
| Checkpoint | LangGraph SQLite Checkpointer |

原项目主要目录：

```text
MEWHELP python/
├── app/
│   ├── api/          # FastAPI 接口
│   ├── core/         # LLM、意图、检索、上下文、飞轮
│   ├── db/           # SQLAlchemy 模型和仓储
│   ├── graph/        # LangGraph 工作流
│   ├── kb/           # 知识库管理
│   ├── schemas/      # Pydantic 请求和响应模型
│   ├── tools/        # Tool 注册、执行、MCP 客户端
│   └── main.py       # 应用入口
├── mcp_servers/      # 原物流和售后 MCP Server
├── scripts/          # 评估、建库、飞轮等离线任务
├── sql/              # 数据库 DDL 和种子数据
├── data/             # 知识库和评估数据
└── tests/            # 单元测试和验收测试
```

## 4. 目标目录结构

迁移到当前仓库后，保留原项目按能力划分的结构，并增加 gRPC Client：

```text
agent-service/
├── app/
│   ├── api/
│   │   ├── chat.py              # /api/chat，SSE 流式聊天
│   │   ├── agent.py             # /api/agent，非流式调用
│   │   ├── actions.py           # interrupt/resume
│   │   ├── conversations.py    # 会话管理
│   │   ├── feedback.py          # 用户反馈
│   │   ├── kb.py                # 知识库管理
│   │   ├── review.py            # 飞轮待审
│   │   └── observability.py     # 观测和成本
│   ├── core/
│   │   ├── llm.py               # ChatOpenAI 等模型客户端
│   │   ├── intent.py            # 意图分类
│   │   ├── coref.py             # 指代消解
│   │   ├── retrieval.py         # 混合检索
│   │   ├── confidence.py        # 证据置信度
│   │   ├── memory.py            # 滑窗、摘要、上下文
│   │   ├── flywheel.py          # 数据飞轮
│   │   └── observability.py     # Langfuse 和指标
│   ├── db/
│   │   ├── models.py            # Agent DB 模型
│   │   ├── repository.py        # Agent DB 仓储
│   │   └── base.py
│   ├── graph/
│   │   ├── state.py             # ConversationState
│   │   ├── nodes.py             # 工作流节点
│   │   ├── routing.py           # 条件路由
│   │   ├── build.py             # 构建图
│   │   └── runtime.py           # run_turn/stream_turn
│   ├── grpc_client/
│   │   ├── __init__.py
│   │   ├── channel.py           # Channel 生命周期和配置
│   │   ├── errors.py            # RPC 错误转换
│   │   ├── context.py           # RequestContext 构造
│   │   ├── business_client.py   # 统一 Business Client
│   │   ├── order_client.py
│   │   ├── logistics_client.py
│   │   ├── aftersales_client.py
│   │   ├── refund_client.py
│   │   ├── ticket_client.py
│   │   └── generated/           # Protobuf 生成代码
│   ├── kb/
│   ├── schemas/
│   ├── tools/
│   │   ├── registry.py
│   │   ├── engine.py
│   │   └── builtin/
│   │       ├── faq.py
│   │       ├── orders.py
│   │       ├── refunds.py
│   │       └── tickets.py
│   ├── config.py
│   └── main.py
├── proto/
│   └── business_service.proto    # 从 Java 服务同步的契约副本
├── tests/
│   ├── unit/
│   ├── graph/
│   ├── grpc/
│   └── integration/
├── pyproject.toml
├── .env.example
└── README.md
```

`grpc_client/generated/` 中的文件由工具生成，不手工修改。源 `.proto` 以 Java 服务中的版本为准，Python 迁移阶段复制同一份文件到 `agent-service/proto/`。

## 5. Agent 工作流

原项目的核心工作流保留，不因为服务拆分而迁移到 Java：

```text
用户消息
  ↓
resolve_reference
  ↓
classify_intent
  ↓
route_by_intent
  ├─ knowledge
  │   └─ retrieve_knowledge
  │       └─ confidence_check
  │           └─ main_agent
  ├─ business
  │   └─ main_agent
  ├─ refund_flow
  │   └─ fetch_order → retrieve_policy → main_agent
  ├─ escalate
  │   └─ complaint_reply
  └─ fallback_script
      └─ script_reply
  ↓
main_agent ⇄ agent_tools
  ↓
log
  ↓
SSE / JSON 响应
```

### 5.1 Agent 节点职责

| 节点 | 职责 |
|---|---|
| `resolve_reference` | 将“那个订单”等指代解析为订单号 |
| `classify_intent` | 识别 knowledge、business、refund、escalate 等意图 |
| `retrieve_knowledge` | 执行向量、BM25、RRF 和重排检索 |
| `confidence_check` | 判断证据是否足够支撑回答 |
| `fetch_order` | 通过 Java gRPC 查询订单上下文 |
| `main_agent` | 调用 LLM，决定是否使用工具 |
| `agent_tools` | 执行 LangChain Tool，并记录审计 |
| `log` | 保存消息、工具调用和工作流结果 |

## 6. 工具边界和迁移映射

### 6.1 保留在 Python 的工具

`query_faq` 保留在 Python，因为 FAQ 和知识检索属于 Agent/Knowledge 能力：

```text
app/tools/builtin/faq.py
    ↓
app/core/retrieval.py
    ↓
Milvus + MySQL knowledge_chunks
```

### 6.2 改造为 gRPC Client 的工具

| 原工具 | 新实现 | Java RPC |
|---|---|---|
| `query_order` | Python Tool 调 OrderClient | `OrderService.QueryOrder` |
| 用户订单列表 | Python Tool 调 OrderClient | `OrderService.ListUserOrders` |
| `query_logistics` | Python Tool 调 LogisticsClient | `LogisticsService.QueryLogistics` |
| `query_warranty` | Python Tool 调 AftersalesClient | `AftersalesService.QueryWarranty` |
| `query_return_status` | Python Tool 调 AftersalesClient | `AftersalesService.QueryReturnStatus` |
| 退款校验 | Python Tool 调 RefundClient | `RefundService.ValidateRefund` |
| `submit_refund` | 用户确认后调用 RefundClient | `RefundService.SubmitRefund` |
| `create_ticket` | 用户确认后调用 TicketClient | `TicketService.CreateTicket` |

### 6.3 原 MCP Server 的处理

原项目中的：

```text
mcp_servers/logistics_server.py
mcp_servers/aftersales_server.py
```

在 Java 业务服务对应能力联调成功后，不再作为 Agent 的主业务调用路径。迁移顺序：

1. 保留 MCP Server，保证旧流程可回滚。
2. 完成 Python gRPC Client 和 Java RPC 联调。
3. 将工具注册从 MCP Tool 切换为 gRPC Tool。
4. 删除或归档 MCP Server。

## 7. Java gRPC 契约

唯一契约文件：

```text
../business-service/src/main/proto/business_service.proto
```

当前包含：

```text
OrderService
├── QueryOrder
└── ListUserOrders

LogisticsService
└── QueryLogistics

AftersalesService
├── QueryWarranty
└── QueryReturnStatus

RefundService
├── ValidateRefund
└── SubmitRefund

TicketService
└── CreateTicket
```

### 7.1 RequestContext

每个请求都必须构造：

```protobuf
message RequestContext {
  string user_id = 1;
  string conversation_id = 2;
  string trace_id = 3;
}
```

字段来源：

| 字段 | 来源 | 是否可信 |
|---|---|---|
| `user_id` | FastAPI 认证上下文或当前开发阶段的用户 Header | 必须由系统注入，不能由模型填写 |
| `conversation_id` | LangGraph 会话 ID | 由 Agent 状态注入 |
| `trace_id` | 请求入口生成或透传 | 由系统生成或透传 |

### 7.2 Python gRPC 依赖

迁移后的 `agent-service/pyproject.toml` 需要增加：

```toml
"grpcio>=1.60.0",
"grpcio-tools>=1.60.0",
```

原项目依赖继续保留：

```toml
"fastapi",
"uvicorn[standard]",
"langchain",
"langchain-openai",
"langgraph",
"sqlalchemy[asyncio]",
"pymilvus[milvus-lite]",
```

如果业务工具全部切换到 Java gRPC，`langchain-mcp-adapters` 和 `mcp` 可以在回滚期保留，正式移除前必须完成旧流程回归测试。

## 8. 生成 Python gRPC 代码

在 `agent-service/` 目录执行：

```powershell
python -m grpc_tools.protoc `
  -I proto `
  --python_out=app/grpc_client/generated `
  --grpc_python_out=app/grpc_client/generated `
  proto/business_service.proto
```

Linux/macOS：

```bash
python -m grpc_tools.protoc \
  -I proto \
  --python_out=app/grpc_client/generated \
  --grpc_python_out=app/grpc_client/generated \
  proto/business_service.proto
```

生成文件：

```text
app/grpc_client/generated/
├── business_service_pb2.py
└── business_service_pb2_grpc.py
```

建议在生成目录增加空的 `__init__.py`，并在生成后修正 `business_service_pb2_grpc.py` 的本地导入，使其适配包路径：

```python
from . import business_service_pb2 as business__service__pb2
```

生成文件不手工添加业务逻辑。

## 9. Python Client 设计

### 9.1 Channel 生命周期

不要在每次工具调用中创建一个新的 Channel。应用启动时创建一个异步 Channel，应用关闭时释放：

```python
class BusinessGrpcClient:
    def __init__(self, target: str):
        self.channel = grpc.aio.insecure_channel(target)
        self.order = OrderServiceStub(self.channel)
        self.logistics = LogisticsServiceStub(self.channel)
        self.aftersales = AftersalesServiceStub(self.channel)
        self.refund = RefundServiceStub(self.channel)
        self.ticket = TicketServiceStub(self.channel)

    async def close(self) -> None:
        await self.channel.close()
```

配置：

```env
BUSINESS_GRPC_TARGET=127.0.0.1:9090
BUSINESS_GRPC_TIMEOUT_SECONDS=3
```

### 9.2 请求构造

```python
def build_context(
    user_id: str,
    conversation_id: str,
    trace_id: str,
) -> RequestContext:
    return RequestContext(
        user_id=user_id,
        conversation_id=conversation_id,
        trace_id=trace_id,
    )
```

### 9.3 订单 Client 示例

```python
class OrderClient:
    def __init__(self, stub: OrderServiceStub, timeout: float):
        self.stub = stub
        self.timeout = timeout

    async def query_order(
        self,
        user_id: str,
        conversation_id: str,
        trace_id: str,
        order_id: str,
    ) -> QueryOrderResponse:
        request = QueryOrderRequest(
            context=RequestContext(
                user_id=user_id,
                conversation_id=conversation_id,
                trace_id=trace_id,
            ),
            order_id=order_id,
        )
        return await self.stub.QueryOrder(
            request,
            timeout=self.timeout,
        )
```

## 10. LangChain Tool 改造规范

模型只允许填写业务参数，身份和链路字段必须由 Tool 执行器注入：

```python
@tool
async def query_order(
    order_id: Annotated[str, "订单号"],
    user_id: Annotated[str, InjectedToolArg],
    conversation_id: Annotated[str, InjectedToolArg],
    trace_id: Annotated[str, InjectedToolArg],
) -> dict:
    response = await order_client.query_order(
        user_id=user_id,
        conversation_id=conversation_id,
        trace_id=trace_id,
        order_id=order_id,
    )

    if not response.success:
        return {
            "ok": False,
            "error_code": response.error_code,
            "message": response.message,
        }

    return {
        "ok": True,
        "order_id": response.order.order_id,
        "status": response.order.status,
        "amount": response.order.amount,
        "product": response.order.product,
        "tracking_no": response.order.tracking_no,
    }
```

Tool 层不应该：

- 让 LLM 自己填写 `user_id`。
- 直接访问 Java 数据库。
- 直接拼接 Protobuf 内部实现对象给 Prompt。
- 吞掉 gRPC 超时和服务不可用异常。

## 11. 错误处理

### 11.1 业务响应错误

Java 响应使用：

```text
success
error_code
message
```

Python 应优先判断 `success` 和 `error_code`，不要依赖中文 message：

```python
if not response.success:
    if response.error_code == "ORDER_NOT_OWNED":
        return {"ok": False, "message": "没有找到您的这笔订单"}
    if response.error_code == "ORDER_NOT_FOUND":
        return {"ok": False, "message": "没有找到您的这笔订单"}
    return {"ok": False, "message": "业务服务暂时不可用"}
```

### 11.2 RPC 传输错误

需要处理：

- `DEADLINE_EXCEEDED`：超时
- `UNAVAILABLE`：Java 服务不可用
- `RESOURCE_EXHAUSTED`：服务限流
- `INTERNAL`：Java 服务内部错误

当前建议：

- 查询类 RPC 可以有限重试一次。
- 退款提交和工单创建不自动重试，必须依赖幂等键。
- 所有 RPC 设置明确 timeout，默认 3 秒。
- RPC 失败必须写入 `tool_audit_logs`。

## 12. 关键业务流程

### 12.1 订单物流查询

```text
用户：订单 1001 的物流到哪了
  ↓
Agent 识别物流意图
  ↓
query_order Tool
  ↓
Java OrderService.QueryOrder
  ↓
得到 tracking_no
  ↓
query_logistics Tool
  ↓
Java LogisticsService.QueryLogistics
  ↓
LLM 组织自然语言回答
  ↓
SSE 返回前端
```

### 12.2 退款确认

```text
用户申请退款
  ↓
Agent 调用 ValidateRefund
  ↓
检索退款政策并组织确认卡片
  ↓
LangGraph interrupt
  ↓
用户确认
  ↓
生成 idempotency_key
  ↓
调用 SubmitRefund
  ↓
Java 再次校验订单归属和状态
  ↓
返回 refund_id
```

推荐幂等键格式：

```text
{conversation_id}-{tool_call_id}
```

### 12.3 创建工单

```text
Agent 收集 description 和 ticket_type
  ↓
interrupt 展示工单预览
  ↓
用户确认
  ↓
调用 CreateTicket
  ↓
Java 检查 idempotency_key
  ↓
返回 ticket_no
  ↓
Agent 更新会话状态为已转人工
```

## 13. Agent DB 数据边界

Python Service 继续拥有 Agent 数据：

| 数据 | Python 是否拥有 |
|---|---:|
| `conversations` | 是 |
| `messages` | 是 |
| `tool_audit_logs` | 是 |
| `low_confidence_questions` | 是 |
| `review_queue` | 是 |
| `eval_runs` | 是 |
| `knowledge_chunks` | 是 |
| `qa_extraction_staging` | 是 |
| `faith_cases` | 是 |
| `topic_classifications` | 是 |
| 订单、物流、退款业务数据 | 否 |

Python 不应直接访问 Java 业务数据源。当前 Java 使用 Mock Mapper，未来接入 Business DB 后也必须通过 gRPC 访问。

## 14. 配置

迁移后的 `.env.example` 至少包含：

```env
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8000

BUSINESS_GRPC_TARGET=127.0.0.1:9090
BUSINESS_GRPC_TIMEOUT_SECONDS=3

CHAT_BASE_URL=
CHAT_API_KEY=
CHAT_MODEL=
EMBED_BASE_URL=
EMBED_API_KEY=
EMBED_MODEL=
RERANK_BASE_URL=
RERANK_API_KEY=
RERANK_MODEL=

MYSQL_DSN=
MILVUS_URI=
LANGFUSE_HOST=
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

密钥只放在本地 `.env`，不得提交到 Git。

## 15. 运行方式

### 15.1 Java 服务

先启动 Java Business Service：

```powershell
cd D:\mewhelp-user-help\business-service
mvn spring-boot:run
```

确认 gRPC 服务：

```powershell
grpcurl -plaintext 127.0.0.1:9090 list
```

### 15.2 Python 服务

迁移完成后：

```powershell
cd D:\mewhelp-user-help\agent-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Python 服务启动前必须保证 `BUSINESS_GRPC_TARGET` 指向 Java 服务。

## 16. 分阶段实施计划

### 阶段 0：迁移原项目

- [ ] 将原 `app/`、`data/`、`sql/`、`scripts/`、`tests/` 迁移到 `agent-service/`
- [ ] 保留原测试套件
- [ ] 在纯英文路径安装并运行原 Python 项目
- [ ] 确认 `/api/chat` 和 `/api/agent` 可用

### 阶段 1：接入 gRPC 基础设施

- [ ] 增加 `grpcio` 和 `grpcio-tools`
- [ ] 同步 `business_service.proto`
- [ ] 生成 Python Stub
- [ ] 创建 Channel 生命周期管理
- [ ] 添加 Java 服务地址和超时配置
- [ ] 用独立脚本调用 `QueryOrder`

### 阶段 2：迁移只读工具

- [ ] 改造 `query_order`
- [ ] 改造 `query_logistics`
- [ ] 改造 `query_warranty`
- [ ] 改造 `query_return_status`
- [ ] 保留 MCP 作为临时回滚路径

### 阶段 3：迁移写工具

- [ ] 接入 `ValidateRefund`
- [ ] 接入 `SubmitRefund`
- [ ] 保留 interrupt/resume
- [ ] 接入 `CreateTicket`
- [ ] 所有写操作使用幂等键
- [ ] 完成重复提交测试

### 阶段 4：清理和联调

- [ ] 删除业务工具对 MCP 的依赖
- [ ] 保留 `query_faq` 本地知识检索
- [ ] 完成订单物流端到端测试
- [ ] 完成退款确认端到端测试
- [ ] 完成工单创建端到端测试
- [ ] 更新 Agent README 和启动脚本

## 17. 验收标准

### 功能

- Python `/api/chat` 可以正常流式回答。
- 用户询问订单时，Agent 能调用 Java `QueryOrder`。
- 用户询问物流时，Agent 能先查订单再查物流。
- 退款流程会等待用户确认，确认后调用 `SubmitRefund`。
- 重复退款请求不会创建多个退款结果。
- 创建工单需要用户确认，重复工单请求不会重复创建。
- FAQ 问题仍然使用 Python 知识库检索。

### 对接

- Python 和 Java 使用同一份 `.proto` 生成代码。
- `user_id`、`conversation_id`、`trace_id` 由系统上下文注入。
- Java 停止时 Python 能返回可理解的服务不可用提示。
- RPC 超时不会无限阻塞 SSE 连接。
- Tool Audit Log 记录工具名、RPC 方法、耗时、错误码和重试次数。

### 性能和稳定性

- 普通业务 RPC 默认超时不超过 3 秒。
- 只读 RPC 最多有限重试一次。
- 写 RPC 不自动重试，依赖幂等键。
- Agent 长连接仍由 Python 管理，不把 SSE 连接转移到 Java。

## 18. 当前限制

- Python Agent Service 尚未迁移到当前仓库。
- 当前 Java 业务服务使用 Mock 数据。
- Java 的退款和工单幂等记录暂存在内存中。
- 当前未接入 JWT、mTLS、服务发现和网关。
- 生成的 gRPC Python 文件必须从 Java 侧契约重新生成，不能手工复制后修改。
