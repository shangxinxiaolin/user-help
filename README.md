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
│   ├── docs/                         # Python 服务规格
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

```text
用户
  │ HTTP / SSE
  ▼
Python Agent Service（规划中）
  ├── FastAPI
  ├── LangGraph
  ├── LangChain Tools
  ├── 知识检索
  └── gRPC Client
        │
        │ gRPC / Protobuf
        ▼
Java Business Service（当前已实现）
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
- Python Agent Service 尚未迁移和联调。

## 环境要求

- JDK 21
- Maven 3.8+
- Python 3.12+，Python Agent 开发阶段使用
- 当前 Mock 阶段不需要 MySQL

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

健康检查：

```http
GET http://127.0.0.1:8080/actuator/health
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

1. 按 Agent 服务职责完善 Python Agent Service 骨架。
2. 重新实现基础 FastAPI、LangGraph 和 LangChain Agent 能力。
3. 根据同一份 `business_service.proto` 生成 Python gRPC Stub。
4. 重新实现订单工具，并改为调用 Java `OrderService`。
5. 依次实现物流、售后、退款和工单工具。
6. 每个阶段完成后与用户确认，再进入下一阶段。
7. 最后再考虑 MyBatis、Business DB、服务治理和性能优化。

## 文档

- [总体拆分规格](docs/SPEC.md)
- [Java Business Service 规格](business-service/docs/JAVA_BUSINESS_SERVICE_SPEC.md)
- [Python Agent Service 规格](agent-service/docs/PYTHON_AGENT_SERVICE_SPEC.md)
- [Java 服务说明](business-service/README.md)
- [Protobuf 接口定义](business-service/src/main/proto/business_service.proto)
- [Python Agent Service 当前状态](agent-service/README.md)

---

**项目名称**：灵犀客服  
**最后更新**：2026-09-27
