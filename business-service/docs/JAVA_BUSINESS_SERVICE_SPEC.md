# MewHelp Java Business Service 规格书

版本：v2.0  
状态：可实施草案  
更新时间：2026-10-06

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
| Java | 开发基线 21；POM java.version=21 与 compiler source/target=17 并存，实际构建目标需单独统一和验证 |
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

Mock 逻辑须保持稳定、可复现，便于跨服务联调：

- 订单号 `1001`、`2002` 是演示订单。
- 订单、物流、售后数据根据业务主键生成稳定结果。
- 订单服务在查询时进行用户归属校验。
- 查询不到订单和订单不属于用户时，对外可统一返回“没有找到您的这笔订单”。
- 退款和工单使用 `idempotency_key` 做进程内幂等。
- 当前幂等记录只保存在内存，进程重启后丢失；这是 Mock 阶段限制。

## 6. gRPC 契约

完整定义位于：`../src/main/proto/business_service.proto`。

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

- 目标是由 Python 校验 JWT/Session 后注入 `user_id`，不能由模型填写；当前开发版 Python 请求可自报 `user_id`，因此这不是已实现的可信认证。
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

当前学习版将身份放在 Protobuf `RequestContext` 中，Java 尚未校验 Agent 服务身份；字段的存在不代表来源可信。对外部署前必须增加服务间认证（如 mTLS 或受保护的共享凭据/签名 metadata），并与 Python 协商是否将用户身份改由可信 metadata 或经 Java 验证的用户令牌传递。不得只凭未经认证的 `RequestContext.user_id` 执行敏感写操作。

### 7.1 Java 服务的访问与授权边界

| 入口 | 当前本地状态 | 对外部署目标 |
|---|---|---|
| gRPC `:9090` | 可用明文调用，尚无服务身份校验 | 仅内部网络可达；先认证调用方再处理 RPC；限制消息大小与超时 |
| HTTP `:8080/api/business/*` | 本地调试，可自报 `X-User-Id` | 不经公网路由；关闭或仅向受认证的管理端开放，不能拿 Header 当作用户认证 |

授权与校验应留在资源所有者 Java 层：订单/物流/售后查询核查归属；退款提交再次检查归属和状态；工单写入检查操作权限；两类写请求的幂等键由 Java 存储和校验。Python 的用户确认卡片只证明前端流程完成，不能替代 Java 的业务授权与幂等校验。对外不通过不同错误暴露订单存在性。

当前 Java Mock 订单、物流、售后和进程内幂等仅支持学习演示，未完成上述全部权限和持久化语义；必须在端到端联调中按接口逐项测试，不能因 Python 已鉴权而跳过 Java 侧复核。

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

唯一配置文件：`../src/main/resources/application.yml`。

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

注意：历史上中文路径曾导致 Windows Protobuf 插件失败；当前工作区是英文路径 `D:\mewhelp-user-help`。若换到中文目录出现路径编码问题，使用纯 ASCII 路径后构建。

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

## 11. 分阶段开发与确认机制

Java Business Service 采用“按业务模块逐步开发、每阶段验收后人工确认”的方式。每个阶段完成后必须向用户汇报并等待明确确认，才能开始下一阶段。

```text
确认当前阶段目标
  ↓
实现当前模块
  ↓
编译和测试
  ↓
汇报变更和结果
  ↓
等待用户确认
  ↓ 用户确认
进入下一阶段
```

建议的 Java 开发阶段：

### Java 阶段 0：项目和契约基础

- 统一根包和启动类
- 确认 Maven 依赖
- 编写并编译 `business_service.proto`
- 启动 gRPC Server
- 用 Apifox 或 grpcurl 查看服务

完成后暂停，确认 Proto 字段、服务名、端口和包结构。

### Java 阶段 1：订单模块

- `order/domain`
- `order/mapper`
- `order/service`
- `order/service/impl`
- `OrderGrpcEndpoint`
- 订单归属校验和订单列表测试

完成后确认订单响应字段和用户归属行为是否满足 Python Tool 对接。

### Java 阶段 2：物流模块

- `logistics/domain`
- `logistics/mapper`
- `logistics/service`
- `logistics/service/impl`
- `LogisticsGrpcEndpoint`
- 根据订单返回的 `tracking_no` 查询物流

完成后确认 Python 是否可以实现“先查订单、再查物流”。

### Java 阶段 3：售后模块

- `aftersales/domain`
- `aftersales/mapper`
- `aftersales/service`
- `aftersales/service/impl`
- `AftersalesGrpcEndpoint`
- 保修和退货状态测试

完成后确认售后状态和错误码是否冻结。

### Java 阶段 4：退款模块

- `refund/domain`
- `refund/mapper`
- `refund/service`
- `refund/service/impl`
- `RefundGrpcEndpoint`
- `ValidateRefund`
- `SubmitRefund`
- 幂等测试和非法状态测试

完成后确认 Python 的 interrupt/resume 是否可以开始接入。

### Java 阶段 5：工单模块

- `ticket/domain`
- `ticket/mapper`
- `ticket/service`
- `ticket/service/impl`
- `TicketGrpcEndpoint`
- 工单参数校验和幂等测试

完成后确认工单字段、会话关联和后续持久化方向。

### Java 阶段 6：Python 联调

- Python 生成同一份 Proto 的 Stub
- 逐个联调订单、物流、售后、退款、工单
- 完成 Apifox、grpcurl 和 Python Tool 三类测试

完成后确认是否保留 HTTP 调试接口、是否删除旧 MCP 路径、是否进入真实数据库设计。

### Java 阶段 7：公网部署前业务服务保护（阶段 6 联调后另行确认）

- 将 gRPC 限制在内部网络，配置服务间认证并拒绝未认证调用。
- 禁止公开 HTTP 调试路由；确需保留时增加可信管理身份验证。
- 对查询接口验证订单/物流/售后的归属，对退款/工单再次验证权限与幂等。
- Python 侧的模型配额与网关限流由各自服务承担；Java 记录业务 RPC 频率与拒绝原因，但不替代 Python 的 Token 费用防护。

验收：外部不能直连业务 RPC/调试接口；未认证内部调用被拒绝；修改 `user_id` 不能越权；重复写请求只有一次业务效果。达到此阶段前不得将服务标为“可公网部署”。

协作规则：

- 用户说“继续”时，先确认当前停在哪个阶段。
- 当前阶段测试未通过时，不进入下一阶段。
- 用户只问问题或要求解释时，不视为阶段确认。
- 删除 MCP、替换 Mock、接入真实数据库都需要单独确认。

## 12. 后续实现顺序

主顺序以仓库 `docs/SPEC.md` 12.6 为准。Java 侧子任务：

1. 冻结实际 Proto 与业务错误码映射，核实 JDK/构建目标。
2. 保留 Mock Mapper，先由 Python Stub 联调 QueryOrder，验收归属和失败结果。
3. 按需联调物流、售后等只读接口，补 endpoint 集成测试。
4. C 阶段经确认后接入 Business DB、退款状态机和持久化幂等；工单持久化按同一边界推进。
5. DTO/VO、监控及部署保护按具体需求补充，不作为 Mock 联调的前置条件。

## 13. 当前明确限制

- 业务数据全部是 Mock，没有真实订单、物流、退款数据库。
- 工单、退款幂等数据只保存在 Java 进程内存中。
- 当前 Java gRPC endpoint 已实现基本调用，但错误码仍需按契约细化。
- 当前明文 gRPC 与 HTTP 调试路由没有服务间认证或可信用户身份，不能直接对公网开放。
- Python 服务已在相邻 `agent-service/` 建立基础聊天与仓储，但仓储 HTTP 接线和 Java gRPC 联调尚未完成，不能宣称端到端客服完成。
