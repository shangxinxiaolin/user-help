# MewHelp Java Business Service 规格书

版本：v2.0  
状态：可实施草案  
更新时间：2026-09-26

## 1. 目标

Java Business Service 是 MewHelp 的业务服务。它由 Python Agent Service 通过 gRPC 调用，负责执行业务查询和写操作；Python 负责对话、意图识别、LangGraph 编排、知识检索和流式输出。

本阶段使用 Mock 数据，目的是先跑通业务链路并学习微服务拆分。接口和包结构按照后续可替换为真实数据库的方式设计。

## 2. 服务边界

### Java 负责

- 订单查询和用户订单列表
- 物流信息查询
- 保修状态和退货状态查询
- 退款资格校验和退款提交
- 工单创建
- 订单归属校验、写操作幂等校验和业务错误码

### Java 不负责

- 用户长连接、SSE 或 WebSocket
- LLM 调用、LangChain、LangGraph
- 意图识别、工具选择和自然语言生成
- FAQ、Milvus 和知识飞轮
- 前端页面

调用关系：

```text
用户
  ↓
Python Agent Service
  ├─ FastAPI
  ├─ LangGraph
  ├─ LangChain Tools
  └─ gRPC Client
       ↓
Java Business Service
  ├─ 业务模块
  ├─ 业务规则
  └─ Mock Mapper
```

## 3. 技术选型

| 项目 | 选择 |
|---|---|
| Java | 21 |
| Web 框架 | Spring Boot 3.2.0 |
| RPC | gRPC 1.60.1 |
| 接口定义 | Protobuf 3.25.1 |
| 数据访问抽象 | Mapper 接口 |
| 当前数据实现 | Mock Mapper + 内存幂等缓存 |
| 未来数据库实现 | MyBatis Mapper |
| HTTP 调试接口 | Spring MVC |

当前没有接入 MySQL。不要为了“看起来完整”提前建立 Business DB；真实数据库接入前先稳定 Protobuf 和业务规则。

## 4. 包结构

项目根包统一为 `com.shangui.userhelp`，参考 `zhiguang` 项目采用按业务模块分包：

```text
src/main/java/com/shangui/userhelp/
├── UserHelpApplication.java
├── common/
│   ├── error/
│   │   ├── BusinessException.java
│   │   └── ErrorCode.java
│   └── web/
│       ├── ApiError.java
│       └── GlobalExceptionHandler.java
├── business/api/
│   └── BusinessController.java
├── order/
│   ├── api/                 # 预留订单专属 HTTP DTO/Controller
│   ├── domain/              # Order
│   ├── mapper/              # OrderMapper、MockOrderMapper
│   └── service/             # OrderService 接口
│       └── impl/            # OrderServiceImpl
├── logistics/
│   ├── api/
│   ├── domain/              # LogisticsInfo
│   ├── mapper/
│   └── service/
│       └── impl/
├── aftersales/
│   ├── api/
│   ├── domain/              # WarrantyInfo、ReturnInfo
│   ├── mapper/
│   └── service/
│       └── impl/
├── refund/
│   ├── api/
│   ├── domain/              # Refund
│   ├── mapper/              # 幂等记录存储抽象
│   └── service/
│       └── impl/
├── ticket/
│   ├── api/
│   ├── domain/              # Ticket
│   ├── mapper/
│   └── service/
│       └── impl/
└── rpc/
    ├── OrderGrpcEndpoint.java
    ├── LogisticsGrpcEndpoint.java
    ├── AftersalesGrpcEndpoint.java
    ├── RefundGrpcEndpoint.java
    └── TicketGrpcEndpoint.java
```

模块内部职责：

- `api`：模块对外 HTTP DTO 或 Controller，避免把协议对象散落在业务代码中。
- `domain`：贫血领域对象，只保存业务数据，不依赖 Spring 或 gRPC。
- `mapper`：数据访问抽象。当前实现 Mock；未来用 MyBatis 实现同一接口。
- `service`：应用服务接口，只定义模块能力。
- `service/impl`：应用服务实现，负责参数校验、权限校验、规则编排和调用 mapper。
- `rpc`：Protobuf 适配层，只负责请求转换、调用业务 service、响应转换。
- `common`：跨模块公共错误和 Web 异常处理。

## 5. Mock 规则

Mock 逻辑必须与原 Python 项目保持可解释性：

- 订单号 `1001`、`2002` 是演示订单。
- 订单、物流、售后数据根据业务主键生成稳定结果。
- 订单服务在查询时进行用户归属校验。
- 查询不到订单和订单不属于用户时，对外可统一返回“没有找到您的这笔订单”。
- 退款和工单使用 `idempotency_key` 做进程内幂等。
- 当前幂等记录只保存在内存，进程重启后丢失；这是 Mock 阶段限制。

## 6. gRPC 契约

完整定义位于：`business-service/src/main/proto/business_service.proto`。

包名为 `mewhelp.business`，Java 生成包为 `com.shangui.userhelp.rpc`。

### 6.1 请求上下文

所有请求使用：

```protobuf
message RequestContext {
  string user_id = 1;
  string conversation_id = 2;
  string trace_id = 3;
}
```

约束：

- `user_id` 由 Python 可信上下文注入，不能由模型填写。
- `conversation_id` 用于会话关联和幂等键生成。
- `trace_id` 用于 Python 和 Java 日志关联。

### 6.2 服务和方法

| Service | RPC | 用途 |
|---|---|---|
| `OrderService` | `QueryOrder` | 查询订单详情 |
| `OrderService` | `ListUserOrders` | 查询用户订单列表 |
| `LogisticsService` | `QueryLogistics` | 按物流单号查询物流 |
| `AftersalesService` | `QueryWarranty` | 查询保修 |
| `AftersalesService` | `QueryReturnStatus` | 查询退货进度 |
| `RefundService` | `ValidateRefund` | 校验能否退款 |
| `RefundService` | `SubmitRefund` | 提交退款 |
| `TicketService` | `CreateTicket` | 创建工单 |

### 6.3 错误码

gRPC 业务响应使用 `success`、`error_code`、`message` 表达业务结果；传输层异常使用 gRPC status。

| error_code | 含义 |
|---|---|
| `INVALID_ARGUMENT` | 参数缺失或格式错误 |
| `ORDER_NOT_FOUND` | 订单不存在 |
| `ORDER_NOT_OWNED` | 订单不属于当前用户 |
| `REFUND_NOT_ALLOWED` | 当前状态不允许退款 |
| `IDEMPOTENCY_KEY_REQUIRED` | 缺少幂等键 |
| `INTERNAL_ERROR` | 内部错误 |

当前 Java 示例 endpoint 对业务异常统一返回 `BUSINESS_ERROR`，下一步应把 `BusinessException.code` 映射为上述稳定错误码，Python 端只依赖错误码，不依赖中文 message。

## 7. Python 对接约定

Python 生成 stub 后，保持长连接和 Agent 状态在 Python；每次工具调用创建普通 unary gRPC 请求。

```python
channel = grpc.aio.insecure_channel("127.0.0.1:9090")
stub = business_service_pb2_grpc.OrderServiceStub(channel)

response = await stub.QueryOrder(
    business_service_pb2.QueryOrderRequest(
        context=business_service_pb2.RequestContext(
            user_id=user_id,
            conversation_id=str(conversation_id),
            trace_id=trace_id,
        ),
        order_id=order_id,
    ),
    timeout=3.0,
)
```

Python Tool 的职责：

1. 从 `InjectedToolArg` 获取 `user_id`、`conversation_id`、`trace_id`。
2. 把模型抽取的订单号、物流号等业务参数写入 Protobuf request。
3. 检查 `success` 和 `error_code`。
4. 把结构化结果转换成 LangGraph 可消费的工具结果。
5. 记录 RPC 延迟和业务错误到 Agent 的 `tool_audit_logs`。

Java 不接收模型直接传来的身份字段作为可信身份；当前学习版将身份放在 request context，后续可增加 gRPC metadata 签名校验。

## 8. HTTP 调试接口

HTTP 接口不是 Python 正式依赖，只用于本地调试：

```text
GET  /api/business/orders/{orderId}
     Header: X-User-Id: u1

GET  /api/business/orders
     Header: X-User-Id: u1

GET  /api/business/logistics/{trackingNo}

GET  /api/business/orders/{orderId}/warranty
GET  /api/business/orders/{orderId}/return-status

POST /api/business/refunds?orderId=1001&reason=不想要了
     Header: X-User-Id: u1
     Header: Idempotency-Key: conv-1-tool-1

POST /api/business/tickets?conversationId=1&description=商品有问题&ticketType=售后
     Header: X-User-Id: u1
     Header: Idempotency-Key: conv-1-tool-2
```

## 9. 配置和运行

唯一配置文件：`business-service/src/main/resources/application.yml`。

```yaml
spring:
  application:
    name: business-service

grpc:
  server:
    port: 9090

app:
  mock:
    enabled: true
```

启动：

```bash
cd business-service
mvn clean test
mvn spring-boot:run
```

注意：当前工作区路径包含中文，`protobuf-maven-plugin` 在 Windows 下可能无法处理中文绝对路径。若本机出现 `Could not make proto path relative`，请把项目放到纯 ASCII 路径后构建，或通过 Windows 开发环境解决路径编码问题。

## 10. 测试要求

当前已覆盖：

- 订单查询和空用户参数校验
- 用户订单列表归属
- 退款幂等
- 工单幂等
- Protobuf 生成和 Java 编译

后续补充：

- gRPC endpoint 集成测试
- Python stub 联调测试
- 订单越权测试
- Java 服务不可用时 Python 的超时和降级测试

## 11. 后续实现顺序

1. 稳定本文件和 `business_service.proto`，不要先改 Python 工具。
2. 为每个业务模块补充 `api/dto/vo`，让 HTTP 调试协议与领域对象分离。
3. 把 `Mock*Mapper` 替换为 MyBatis 实现，接口保持不变。
4. 将 Java endpoint 的错误码细化为契约中的稳定错误码。
5. Python 生成同一份 proto 的 stub，先联调 `QueryOrder`。
6. 依次联调物流、售后、退款和工单。

## 12. 当前明确限制

- 业务数据全部是 Mock，没有真实订单、物流、退款数据库。
- 工单、退款幂等数据只保存在 Java 进程内存中。
- 当前 Java gRPC endpoint 已实现基本调用，但错误码仍需按契约细化。
- 当前 Python Agent Service 尚未迁移到本目录，不能宣称端到端客服已经完成。
