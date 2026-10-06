# 灵犀客服

> 面向微服务架构的智能客服学习项目

灵犀客服计划将 AI Agent 与业务服务拆分：Python 负责对话理解、LangGraph 编排和工具调用；Java 负责订单、物流、售后、退款和工单等业务能力。

Java Business Service 已提供 Mock 业务接口。Python Agent Service 正按目标架构逐步实现，目前已完成基础对话、会话/消息 ORM 与仓储；业务工具与 Java gRPC 尚未联调。

## 项目结构

```text
lingxi-customer-service/
├── business-service/                 # Java Business Service，当前主要实现
│   ├── src/main/java/com/shangui/userhelp/
│   │   ├── common/                   # 公共错误和 Web 异常处理
│   │   ├── business/api/             # HTTP 调试接口
│   │   ├── order/                    # 订单模块
│   │   │   ├── domain/
│   │   │   ├── mapper/
│   │   │   └── service/impl/
│   │   ├── logistics/                # 物流模块
│   │   ├── aftersales/               # 售后模块
│   │   ├── refund/                   # 退款模块
│   │   ├── ticket/                   # 工单模块
│   │   └── rpc/                      # gRPC Endpoint
│   ├── src/main/proto/
│   │   └── business_service.proto   # Java/Python 共用的接口契约
│   ├── src/test/                     # 业务单元测试
│   ├── pom.xml
│   └── README.md
│
├── agent-service/                    # Python Agent Service，按原能力重新实现
│   ├── app/                          # API、Graph、模型与数据库层
│   ├── docs/                         # Python 服务规格与模块设计
│   ├── scripts/                      # 手动联调检查
│   ├── sql/                          # Agent DB 建表脚本
│   ├── tests/                        # 单元/仓储测试
│   ├── pyproject.toml
│   └── README.md
│
├── docs/
│   └── SPEC.md                       # 总体架构规格
│
└── README.md
```

## 架构

**目标架构已确定，E 阶段尚未实现**：Gateway/BFF 与业务模块同处一个 Spring Boot 项目和进程，Python 是内部 Agent 服务。

```text
客户端 → HTTPS → Spring Boot
                  ├─ entry：认证鉴权、限流、产品路由、Agent SSE 转发
                  ├─ 普通请求 → 业务 Service → Business DB
                  └─ Agent 请求 → 内部 HTTP/SSE → Python Agent
                                                  ├─ 会话 / Graph / RAG / checkpoint
                                                  └─ gRPC → 同一 Spring Boot 的 Business RPC
```

当前开发仍直接请求 Python JSON 接口；SSE 和 Java Agent 转发待实现，Java HTTP 目前仅为业务调试。Java 入口不复制 Python 会话状态，调用 Agent 时不持有业务事务；Python 只回调 Business RPC，不回调 Agent 入口。下面是统一入口实施前的开发链路与能力规划：

```text
用户
  │ HTTP / SSE
  ▼
Python Agent Service（逐步实现）
  ├── FastAPI
  ├── LangGraph 工作流
  │     （指代消解 → 意图识别 → 分流 → 检索 → 置信度闸 → 主力 Agent → 日志）
  ├── 知识检索（向量 + BM25 + 重排）
  ├── 会话上下文（三层分层：原文 / 截短 / 摘要）
  ├── 可观测 + 数据飞轮
  ├── LangChain Tools + MCP
  └── gRPC Client
        │
        │ gRPC / Protobuf
        ▼
Java Business Service（Mock 已实现）
  ├── order
  ├── logistics
  ├── aftersales
  ├── refund
  └── ticket
        │
        ▼
当前：Mock Mapper
后续：MyBatis + Business DB
```

## 当前完成情况

Java Business Service 已完成：

- Spring Boot 项目骨架
- 按业务模块分包
- `service` 接口与 `service/impl` 实现分离
- 订单查询和用户订单列表
- 物流查询
- 保修和退货状态查询
- 退款校验和提交
- 退款幂等
- 工单创建和工单幂等
- HTTP 调试接口
- gRPC 服务端
- Protobuf Java 代码生成
- 单元测试
- Maven 测试和打包

当前限制：

- 业务数据全部是 Mock 数据。
- 当前没有 Business DB。
- 退款和工单幂等记录只保存在 Java 进程内存中。
- Python 已有基础聊天、会话/消息模型与仓储、SQLite checkpoint；HTTP 入口尚未注入仓储，业务 gRPC 尚未联调。

## 环境要求

- JDK 21
- Maven 3.8+
- Python 3.12+，Python Agent 开发阶段使用
- Java Mock 阶段不需要 MySQL；Python 仓储验证需要独立的 Agent MySQL 数据库。

建议将项目放在纯英文路径，例如：

```text
D:\mewhelp-user-help
```

Windows 下 Protobuf Maven 插件可能无法正确处理中文路径。

## 启动 Java Business Service

```bash
cd D:\mewhelp-user-help\business-service
mvn clean test package
java -jar target\business-service-1.0.0-SNAPSHOT.jar
```

开发模式也可以使用：

```bash
mvn spring-boot:run
```

服务端口：

```text
HTTP: 8080
gRPC: 9090
```

## 编译 Protobuf

Proto 文件：

```text
business-service/src/main/proto/business_service.proto
```

生成 Java 消息类和 gRPC 服务类：

```bash
cd D:\mewhelp-user-help\business-service
mvn generate-sources
```

生成目录：

```text
target/generated-sources/protobuf/java
target/generated-sources/protobuf/grpc-java
```

完整编译：

```bash
mvn clean compile
```

## HTTP 调试接口

HTTP 调试可用性检查（当前 POM 未声明 Actuator，不能将 `/actuator/health` 当作可用端点）：

```http
GET http://127.0.0.1:8080/api/business/orders/1001
X-User-Id: u1
```

查询订单：

```http
GET http://127.0.0.1:8080/api/business/orders/1001
X-User-Id: u1
```

查询订单列表：

```http
GET http://127.0.0.1:8080/api/business/orders
X-User-Id: u1
```

查询物流：

```http
GET http://127.0.0.1:8080/api/business/logistics/{trackingNo}
```

提交退款：

```http
POST http://127.0.0.1:8080/api/business/refunds?orderId=1001&reason=不想要了
X-User-Id: u1
Idempotency-Key: conv-1-refund-1
```

创建工单：

```http
POST http://127.0.0.1:8080/api/business/tickets?conversationId=123&description=商品有问题&ticketType=售后
X-User-Id: u1
Idempotency-Key: conv-1-ticket-1
```

## gRPC 调试

使用 `grpcurl` 查看服务：

```bash
grpcurl -plaintext 127.0.0.1:9090 list
```

查询订单：

```bash
grpcurl -plaintext -d "{\"context\":{\"user_id\":\"u1\",\"trace_id\":\"test-001\"},\"order_id\":\"1001\"}" 127.0.0.1:9090 mewhelp.business.OrderService/QueryOrder
```

查询物流：

```bash
grpcurl -plaintext -d "{\"context\":{\"user_id\":\"u1\",\"trace_id\":\"test-002\"},\"tracking_no\":\"SF123456789\"}" 127.0.0.1:9090 mewhelp.business.LogisticsService/QueryLogistics
```

## 测试

```bash
cd D:\mewhelp-user-help\business-service
mvn test
```

当前测试覆盖订单查询、用户订单列表、退款幂等和工单幂等。

## 后续计划

按能力分阶段推进，每阶段完成测试、汇报并等待确认后再进入下一阶段（详见 `docs/SPEC.md` 12.6 分阶段实施与验收）：

下列 A–E 是能力标签；具体学习/实施顺序统一以总规格 12.6 为准，不强制按字母顺序。

1. **A 基础接线（尚未验收）**：基础对话、会话/消息 ORM、仓储与 checkpoint 封装已存在；还需通过 FastAPI Depends 接通 HTTP 仓储注入，验证归属拒绝、消息落库和重启恢复。
2. **B 只读业务链**：Python 工具 → gRPC → Java 查询订单。
3. **C 可靠退款**：确认状态 + Java 持久化退款与幂等。
4. **D 政策依据与评测**：小范围政策 RAG、引用与低置信度处理。
5. **E 统一产品入口**：在当前 Spring Boot 内新增 entry Gateway/BFF，验证客户端身份并通过内部 HTTP/SSE 调 Python；Python 通过 gRPC 调业务。目标已确定，协议和实施另行验收。

各模块的设计与选型理由见 `agent-service/docs/design/`（01–10 篇），总体架构与契约见 `docs/SPEC.md`。

## 文档

- [总体拆分规格](docs/SPEC.md)
- [模块设计与选型（10 篇）](agent-service/docs/design/)
- [Java Business Service 规格](business-service/docs/JAVA_BUSINESS_SERVICE_SPEC.md)
- [Python Agent Service 规格](agent-service/docs/PYTHON_AGENT_SERVICE_SPEC.md)
- [Java 服务说明](business-service/README.md)
- [Protobuf 接口定义](business-service/src/main/proto/business_service.proto)
- [Python Agent Service 当前状态](agent-service/README.md)

---

**项目名称**：灵犀客服  
**最后更新**：2026-10-06
