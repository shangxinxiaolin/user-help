# 灵犀客服 Python Agent Service 规格书

版本：v1.0  
状态：分阶段实施规格
更新时间：2026-10-06

## 1. 文档目的

本文档定义灵犀客服 Python Agent Service 的职责、目录结构、运行方式、Agent 工作流、工具实现方案，以及与 Java Business Service 的 gRPC 对接契约。

项目目录：

```text
D:\mewhelp-user-help\agent-service
```

当前 `agent-service/` 已完成基础对话、Graph 消息状态和会话/消息仓储；完整工作流、SSE、知识库及 Java gRPC 联调仍在后续阶段。

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

目标部署已确定为：客户端 → Spring Boot entry（Gateway/BFF 与业务同一项目/进程）→ 内部 HTTP/SSE → Python → gRPC → Java Business。E 阶段尚未实现；下图保留本地开发的直连方式，不是最终公网入口。Python 不负责客户端登录，负责验证 Java 服务及受保护用户上下文，并维护会话归属。

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

## 3. 技术栈与能力规划

Agent Service 使用 Python 3.12+；下表同时列出已接入和后续阶段需要的能力：

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

服务代码按技术职责组织：

```text
agent-service/
├── app/
│   ├── api/          # FastAPI 接口
│   ├── core/         # LLM、意图、检索、上下文、飞轮
│   ├── db/           # SQLAlchemy 模型和仓储
│   ├── graph/        # LangGraph 工作流
│   ├── kb/           # 知识库管理
│   ├── schemas/      # Pydantic 请求和响应模型
│   ├── tools/        # Tool 注册、执行、MCP 客户端
│   └── main.py       # 应用入口
├── app/grpc_client/  # Java Business Service RPC 客户端（规划）
├── scripts/          # 评估、建库、飞轮等离线任务
├── sql/              # 数据库 DDL 和种子数据
├── data/             # 知识库和评估数据
└── tests/            # 单元测试和验收测试
```

## 4. 目标目录结构

各模块按职责逐步实现，业务能力通过 gRPC Client 接入：

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
│   │   ├── memory.py            # 三层分层：原文/截短/摘要
│   │   ├── flywheel.py          # 数据飞轮
│   │   └── observability.py     # Langfuse 和指标
│   ├── db/
│   │   ├── models/              # Agent DB 模型包
│   │   ├── repositories/        # Agent DB 仓储包
│   │   └── base.py
│   ├── graph/
│   │   ├── state.py             # ConversationState
│   │   ├── answer.py            # 最终回答解析
│   │   ├── nodes/
│   │   │   ├── chat.py          # 基础聊天节点
│   │   │   ├── intent.py        # 指代消解、意图分类
│   │   │   ├── knowledge.py     # 检索、置信度闸
│   │   │   ├── business.py      # 订单、物流等编排
│   │   │   ├── refund.py        # 退款子流程
│   │   │   └── tools.py         # 工具执行节点
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
│   ├── core/config.py          # 位于 core 包的配置文件
│   └── main.py
├── proto/
│   └── business_service.proto    # 从 Java 服务同步的契约副本
├── tests/
│   ├── api/
│   ├── core/
│   ├── graph/
│   ├── schemas/
│   ├── grpc/
│   ├── integration/
│   └── fakes.py                  # 统一测试模型和替身
├── pyproject.toml
├── .env.example
└── README.md
```

`grpc_client/generated/` 中的文件由工具生成，不手工修改。源 `.proto` 以 Java 服务中的版本为准，Python 迁移阶段复制同一份文件到 `agent-service/proto/`。

## 5. Agent 工作流

目标工作流由 Agent Service 编排，不迁移到 Java：

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

| Agent 工具 | 实现方式 | Java RPC |
|---|---|---|
| `query_order` | Python Tool 调 OrderClient | `OrderService.QueryOrder` |
| 用户订单列表 | Python Tool 调 OrderClient | `OrderService.ListUserOrders` |
| `query_logistics` | Python Tool 调 LogisticsClient | `LogisticsService.QueryLogistics` |
| `query_warranty` | Python Tool 调 AftersalesClient | `AftersalesService.QueryWarranty` |
| `query_return_status` | Python Tool 调 AftersalesClient | `AftersalesService.QueryReturnStatus` |
| 退款校验 | Python Tool 调 RefundClient | `RefundService.ValidateRefund` |
| `submit_refund` | 用户确认后调用 RefundClient | `RefundService.SubmitRefund` |
| `create_ticket` | 用户确认后调用 TicketClient | `TicketService.CreateTicket` |

### 6.3 MCP 工具边界

订单、物流、售后、退款与工单由 Java gRPC 提供；MCP 仅用于可插拔的外部动态工具，避免同一业务能力存在两条相互冲突的调用链。MCP 客户端在外部工具阶段按需接入。

## 7. Java gRPC 契约

唯一契约文件：

```text
business-service/src/main/proto/business_service.proto（相对于仓库根）
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
| `user_id` | Java entry 验证客户端身份，Python 验证内部上下文后注入；目前由本地请求提供 | 当前未认证；目标须验证来源，模型不可填写 |
| `conversation_id` | LangGraph 会话 ID | 由 Agent 状态注入 |
| `trace_id` | 请求入口生成或透传 | 由系统生成或透传 |

### 7.2 Python gRPC 依赖

迁移后的 `agent-service/pyproject.toml` 需要增加：

```toml
"grpcio>=1.60.0",
"grpcio-tools>=1.60.0",
```

Agent 基础依赖：

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

生成目录需要 `__init__.py`。生成脚本应自动适配包内导入，不由开发者每次手工编辑生成文件；所需结果如下：

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

### 11.0 公网接口边界与模型额度保护

**当前状态**：本地 FastAPI 尚未实现 JWT、限流和 Token 配额；请求里的 `user_id` 可由调用方自报，只能用于本地调试。当前 `/api/chat` 还是非流式 JSON，尚未迁至本节描述的 SSE 目标形态。不得将此实现直接暴露公网。

**对外部署目标**：

| 接口 | 访问范围 | 调用模型前必须完成的检查 |
|---|---|---|
| `POST /api/chat` | Java entry 内部调用；前端经 Java 转发 | Java 服务/用户上下文、会话归属、请求大小、模型并发和预算 |
| `POST /api/agent` | 内网或管理员 | 服务/管理员身份、会话归属、额度；网关不转发普通公网流量 |
| `POST /api/actions/resume` | Java 转发原会话用户请求 | 内部上下文与会话归属、幂等与并发控制 |
| 管理/知识审核接口 | 管理员 | 管理员身份和操作权限 |
| `GET /health` | 运维或网关 | 不调用模型，不暴露密钥/内部状态 |

客户端 Body 不携带可信身份，JWT/Session 由 Java entry 验证。Java 传递受保护、限时且限定接收方的用户上下文，Python 验证服务身份及上下文后注入 State，并在续聊/resume 前核查 conversations.user_id。裸 X-User-Id 不作为认证。具体内部协议、Schema 和客户端迁移在 E 阶段冻结；当前 Body user_id 仅为开发契约。

所有入口的模型预算检查必须发生在 Graph/LLM 调用之前：

1. 边缘层（网关/反向代理）限制 IP 频率、请求体大小与 TLS；Python 再实施用户级限流，不能只靠 IP。
2. 对消息长度、模型输入上下文和单次最大输出 Token 分别设上限；`max_agent_steps` 限制 ReAct 循环，工具/模型请求均设 deadline。
3. 对每用户的时间窗请求数、活跃 SSE 连接、并发 LLM 调用、每日 Token/费用预算，以及全局并发设置**可配置**上限。多实例时通过共享存储原子占额和释放，不能用各进程独立内存计数宣称全局生效。
4. 发起模型请求前预留预算；根据模型实际返回的 usage（含失败/取消时可获取的用量）结算。取消不保证上游不计费，应做账务对账；异常与客户端断开时释放并发槽位。
5. 客户端断开 SSE 时取消本地 Graph/LLM 任务、避免继续生成；给 SSE 空闲和整体生命周期设置上限。模型 429/5xx 不可无限重试，以免放大成本。

认证或配额失败发生在响应头发送**之前**时使用 HTTP 401（未认证）、403/404（无权/会话归属）、413（Body 过大）、422（参数错误）、429（频率/并发/额度）；模型/后端不可用按 502/503/504 处理。SSE 响应开始后不能再改 HTTP 状态码，必须发送 `error` 事件并结束流。不要将完整 Prompt、密钥或隐私内容写入限流日志。

建议配置键（均为待实现项，数值应通过预算和负载测试确定，而非当前承诺）：

```env
CHAT_REQUEST_TIMEOUT_SECONDS=<按上游实测确定>
CHAT_MAX_INPUT_CHARS=<按业务确定>
CHAT_MAX_OUTPUT_TOKENS=<按成本确定>
MAX_AGENT_STEPS=<按工作流确定>
USER_REQUESTS_PER_MINUTE=<按套餐确定>
USER_MAX_CONCURRENT_CHATS=<按容量确定>
GLOBAL_MAX_CONCURRENT_LLM_CALLS=<按容量确定>
USER_DAILY_TOKEN_QUOTA=<按预算确定>
REDIS_URL=<多实例共享计数时配置>
```

建议阶段顺序：先完成可信身份和会话归属、输入/输出预算、LLM/Graph 超时及单实例并发控制；公网发布前补齐共享限流和额度结算、边缘入口保护、SSE 取消处理及对应验收。以上措施都尚未实现。

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

DATABASE_URL=mysql+asyncmy://root:CHANGE_ME_MYSQL_PASSWORD@127.0.0.1:3307/lingxi_agent
TEST_DATABASE_URL=mysql+asyncmy://root:CHANGE_ME_MYSQL_PASSWORD@127.0.0.1:3307/lingxi_agent_test
CHECKPOINTER_DB_PATH=data/checkpoints.sqlite
MILVUS_URI=
LANGFUSE_BASE_URL=
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
uv sync --group dev
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Python 服务启动前必须保证 `BUSINESS_GRPC_TARGET` 指向 Java 服务。

## 16. 分阶段实施计划

主实施顺序以仓库总规格 `docs/SPEC.md` 12.6 为准；下列编号为早期服务子任务，未勾选框不代表已有能力尚未实现。当前 A 的 HTTP 仓储注入尚未验收。最新范围：FastAPI Depends、真实 API 运行与替身测试、Milvus Standalone、批处理飞轮及完整审核接口/页面；微调暂不实施。

本项目采用“单阶段交付、阶段闸门确认”的开发方式。每个阶段只完成当前阶段范围内的代码和测试；阶段验收完成后，必须把结果、变更文件、测试结果和遗留问题告诉用户，并等待用户明确确认，才能进入下一阶段。

未经用户确认，不得自行跨阶段实现后续功能。例如：完成 gRPC Client 后，不自动改造退款流程；完成订单工具后，不自动删除 MCP Server。

每个阶段的固定流程如下：

```text
明确本阶段目标
  ↓
实施本阶段代码
  ↓
运行本阶段测试
  ↓
汇报结果和问题
  ↓
等待用户确认
  ↓ 用户同意
进入下一阶段
```

阶段汇报至少包含：

- 本阶段完成的功能
- 修改和新增的文件
- 执行过的命令及结果
- 与 Java 服务的接口变化
- 尚未解决的问题
- 下一阶段准备做什么
- 需要用户确认的设计选择

用户确认可以使用以下明确表达：

- “进入下一阶段”
- “继续做阶段 2”
- “确认，继续”

如果用户只提出问题、要求解释或要求修改当前阶段，仍然停留在当前阶段，不视为进入下一阶段。

### 阶段 0：创建新项目骨架

**阶段闸门：完成后必须与用户确认。**

- [ ] 创建 `app/api`、`app/core`、`app/graph`、`app/tools`、`app/kb`、`app/db`、`app/schemas`
- [ ] 创建新的 `pyproject.toml` 和 `.env.example`
- [ ] 创建 FastAPI 应用和 `/health` 接口
- [ ] 创建 LangGraph 的 State、节点和构图骨架
- [ ] 创建最小 `/api/chat` 接口
- [ ] 按服务职责实现独立模块

本阶段不接入 Java gRPC，不调用真实 LLM，不实现完整业务工具。目标是先建立新项目的运行骨架，并让你理解 FastAPI、Pydantic 和 LangGraph 的基本结构。

完成后需要与用户确认：

1. 新 Python 服务是否可以启动。
2. `/health` 和最小 `/api/chat` 是否可用。
3. 是否接受按服务职责划分的目录结构。
4. 是否允许进入阶段 1。

本阶段的教学顺序：

1. 先解释 `pyproject.toml`、虚拟环境和依赖安装。
2. 再创建 FastAPI `main.py` 和 `/health`。
3. 再创建 Pydantic 请求/响应模型。
4. 再创建 LangGraph 的 State、Node 和 Graph。
5. 最后把最小 Graph 接入 `/api/chat`。

每完成一个小步骤都可以运行一次测试和启动检查；如果用户提出疑问，停留在当前小步骤解释清楚，不自动跳过。

### 阶段 1：复刻基础 Agent 对话能力

**阶段闸门：完成后必须与用户确认。**

- [ ] 实现基础 Prompt 和 LLM 客户端抽象
- [ ] 实现 LangGraph 的消息状态
- [ ] 实现普通对话节点
- [ ] 实现 `/api/chat` 的流式响应
- [ ] 为节点和 API 添加单元测试

本阶段完善基础 Agent 对话能力，不接业务 RPC，以便先验证状态、节点和流式输出。

完成后需要与用户确认：

1. 新 Agent 是否能完成一轮普通对话。
2. LangGraph 状态和节点职责是否清晰。
3. 流式输出和测试是否符合预期。
4. 是否允许进入阶段 2。

### 阶段 2：接入 gRPC 基础设施并实现订单工具

**阶段闸门：完成后必须与用户确认。**

- [ ] 增加 `grpcio` 和 `grpcio-tools`
- [ ] 同步 `business_service.proto`
- [ ] 生成 Python Stub
- [ ] 创建 Channel 生命周期管理
- [ ] 添加 Java 服务地址和超时配置
- [ ] 实现 `OrderClient`
- [ ] 实现新的 `query_order` Tool
- [ ] 将订单 Tool 接入 LangGraph

本阶段只实现订单调用，顺序为：

```text
生成 Stub
  ↓ 用户确认
QueryOrder RPC Client
  ↓ 用户确认
query_order Tool
  ↓ 用户确认
接入 Agent 工作流
```

每完成一个工具，都应单独测试后与用户确认；不能一次性跳过中间确认。

完成本阶段后需要与用户确认：

1. Python 是否能独立调用 Java `QueryOrder`。
2. 订单 Tool 返回格式是否满足 Agent Prompt 使用。
3. 订单归属错误是否能正确返回。
4. 是否允许进入阶段 3。

### 阶段 3：实现物流和售后只读工具

**阶段闸门：完成后必须与用户确认。**

- [ ] 实现 `LogisticsClient`
- [ ] 实现 `query_logistics`
- [ ] 实现 `AftersalesClient`
- [ ] 实现 `query_warranty`
- [ ] 实现 `query_return_status`
- [ ] 将只读工具接入 Agent 工作流

每完成一个工具，都要单独测试并等待确认：

```text
物流 QueryLogistics
  ↓ 用户确认
售后 QueryWarranty / QueryReturnStatus
```

完成后确认订单→物流链路和售后查询是否符合预期。

### 阶段 4：实现退款确认流程

**阶段闸门：完成后必须与用户确认。**

- [ ] 实现 `ValidateRefund`
- [ ] 实现 `SubmitRefund`
- [ ] 保留 interrupt/resume
- [ ] 生成幂等键
- [ ] 完成重复提交和非法状态测试

完成后需要与用户确认：

1. 退款确认卡片和恢复流程是否符合预期。
2. 重复提交是否保持幂等。
3. 是否允许进入阶段 5。

### 阶段 5：实现工单流程

- [ ] 实现 `CreateTicket`
- [ ] 实现工单预览和 interrupt/resume
- [ ] 接入会话状态更新
- [ ] 完成工单幂等测试

完成后确认是否进入阶段 6。

### 阶段 6：清理和端到端联调

- [ ] 完成订单、物流、售后、退款、工单端到端测试
- [ ] 保留 `query_faq` 本地知识检索
- [ ] 决定是否删除或保留原 MCP Server
- [ ] 更新 README 和启动脚本
- [ ] 记录所有已知限制

只有用户确认阶段 5 完成后，才允许删除或停用旧 MCP 业务路径。

### 阶段 7：公网接入与模型费用防护（需单独确认）

- [ ] Java entry 验证客户端 JWT/Session；Python 验证内部服务/用户上下文并校验会话归属，移除 Body 自报身份。
- [ ] 对普通用户关闭 `/api/agent` 与管理接口的公网路由。
- [ ] 配置消息/请求体长度、模型输出 Token、单次超时和最大 Agent 步数。
- [ ] 增加用户频率、用户/全局并发、活跃 SSE 连接及每日 Token 配额；多实例采用共享的原子计数。
- [ ] 在开始调用模型前预占预算，并根据实际 usage 结算；对客户端断开、超时及失败做释放和对账。
- [ ] 接入网关/反向代理的 TLS、IP 限流与路径白名单；与 Java 服务完成服务间认证。
- [ ] 运行本文件“对外部署前安全验收”的所有测试。

阶段 6 只验收本地功能，不能代替阶段 7 的公网发布验收。进入阶段 7 和对公网开放必须分别得到用户确认。

## 16.1 开发协作规则

后续每次开发只处理用户当前确认的阶段。用户提出“继续”时，应先确认当前阶段和剩余验收项；如果当前阶段尚未验收，优先完成当前阶段，不擅自进入后续阶段。

默认每次只修改或新增一个文件，检查并汇报后等待确认。用户明确授权批量修改时，可在授权范围内一次处理多个文件并统一验收；文档修复授权不等于代码修改授权。

每次阶段交付后的最终回复必须以“当前停在阶段闸门，等待你的确认”结束，除非用户已经明确授权进入下一阶段。

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

### 对外部署前安全验收（待实现）

- 未认证请求在模型调用前返回 401；修改 Body 中的 `user_id` 无法冒充他人。
- 访问、续跑他人的 `conversation_id` 被拒绝，且不进入 Graph。
- 超长请求在模型调用前被拒绝，配额、频率或并发超限返回 429，模型调用次数保持不变。
- `/api/agent` 无法作为普通公网接口调用；管理路径需要管理员权限。
- SSE 断开、超时和模型故障均释放并发槽位；断开后不继续本地生成任务，实际用量仍入账。
- 多实例并发或额度使用共享原子计数验证，不依赖单机计数结果。

### 性能和稳定性

- 普通业务 RPC 默认超时不超过 3 秒。
- 只读 RPC 最多有限重试一次。
- 写 RPC 不自动重试，依赖幂等键。
- Graph 执行与内部流由 Python 管理；浏览器连接由 Java entry 管理和转发，双方释放各自资源。
- Python 管理 Agent 执行及内部流；E 阶段 Java 同时持有浏览器 SSE 连接并转发 Python 流，双方各自释放连接/任务资源。不得将“Python 保有执行状态”误解为“Java 不接长连接”。

## 18. 当前限制

- Python Agent Service 已具备基础聊天、ORM 与仓储，但完整路由、RAG、工具和 SSE 尚未完成。
- HTTP 入口尚未传入 repository，归属查询与消息落库未在 API 主链路生效；SQLite checkpoint 可独立恢复同一 thread 的 Graph 消息，不等于已经实现 interrupt/resume。
- 当前 Java 业务服务使用 Mock 数据。
- Java 的退款和工单幂等记录暂存在内存中。
- 当前未接入 JWT、mTLS、服务发现和网关。
- 当前没有用户限流、并发/Token 配额、请求长度或 SSE 断连取消保护；不得直接公网开放。
- 生成的 gRPC Python 文件必须从 Java 侧契约重新生成，不能手工复制后修改。
