# 灵犀客服

> 面向微服务架构的智能客服系统

灵犀客服将对话理解与业务执行解耦：Python Agent 负责意图识别、知识检索和工具编排，Java Business Service 负责订单、物流、售后、退款和工单等业务能力。

## 🏗️ 项目结构

```
user-help/
├── docs/                           # 📚 文档目录
│   ├── SPEC.md                     # 微服务拆分总体规格书
│   ├── JAVA_BUSINESS_SERVICE_SPEC.md   # Java 服务详细规格
│   ├── PYTHON_AGENT_SERVICE_SPEC.md    # Python 服务详细规格
│   └── architecture/               # 架构图和设计图
│
├── business-service/               # ☕ Java Business Service
│   ├── src/main/java/com/mewhelp/business/
│   │   ├── domain/                 # 领域层（订单、物流、售后等）
│   │   ├── application/            # 应用层（应用服务）
│   │   ├── infrastructure/         # 基础设施层（Mock 仓储、数据库）
│   │   └── interfaces/             # 接口层（gRPC 服务实现）
│   ├── src/main/proto/             # Protobuf 接口定义
│   ├── pom.xml                     # Maven 配置
│   └── README.md
│
├── agent-service/                  # 🐍 Python Agent Service
│   ├── app/
│   │   ├── graph/                  # LangGraph 工作流定义
│   │   ├── tools/                  # LangChain Tools 实现
│   │   ├── grpc_client/            # gRPC Client 封装
│   │   └── api/                    # FastAPI 路由
│   ├── requirements.txt            # Python 依赖
│   └── README.md
│
├── proto/                          # 🔗 共享 Protobuf 定义
│   └── business_service.proto      # 服务接口契约
│
└── README.md                       # 项目总览（本文件）
```

## 🎯 架构设计

### 服务拆分方案

```
┌─────────────────────────────────────────────────────────────┐
│                         用户前端                              │
│                    (WebSocket / SSE)                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Python Agent Service (FastAPI)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  LangGraph 工作流编排                                  │   │
│  │  - 意图识别                                             │   │
│  │  - 工具调用编排                                         │   │
│  │  - 知识库检索 (Milvus)                                 │   │
│  │  - 流式输出                                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         │ gRPC 调用                          │
│                         ▼                                    │
└─────────────────────────────────────────────────────────────┘
                         │
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          Java Business Service (Spring Boot)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  业务能力提供                                           │   │
│  │  - 订单查询                                             │   │
│  │  - 物流查询                                             │   │
│  │  - 售后处理                                             │   │
│  │  - 退款流程                                             │   │
│  │  - 工单创建                                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│                  Mock 数据 / MySQL                           │
└─────────────────────────────────────────────────────────────┘
```

### 服务职责

| 服务 | 职责 | 技术栈 |
|------|------|--------|
| **Python Agent Service** | 对话编排、意图识别、工具调用、知识库检索、流式输出 | FastAPI + LangGraph + LangChain + Milvus |
| **Java Business Service** | 订单管理、物流查询、售后处理、退款流程、工单创建 | Spring Boot + gRPC + MySQL |

### 通信方式

- **gRPC**：Python Agent Service ↔ Java Business Service
- **WebSocket / SSE**：前端 ↔ Python Agent Service
- **Protobuf**：服务间接口定义

## 🚀 快速开始

### 前置要求

- **Java**: JDK 17+
- **Python**: 3.10+
- **Maven**: 3.8+
- **MySQL**: 8.0+ (可选，Mock 阶段不需要)

### 启动 Java Business Service

```bash
cd business-service
mvn clean install
mvn spring-boot:run

# 验证 gRPC Server 启动
# 应该监听在 localhost:9090
```

### 启动 Python Agent Service

```bash
cd agent-service

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python main.py

# 应该监听在 localhost:8000
```

## 📋 开发阶段

### 阶段 1：Java Mock Service (当前)

- ✅ 搭建 Java Spring Boot 项目框架
- ✅ 定义 Protobuf 接口
- ⏳ 实现 gRPC Server
- ⏳ Mock 数据生成器
- ⏳ 订单归属校验逻辑

### 阶段 2：Python Agent 适配

- ⏳ Python gRPC Client 封装
- ⏳ LangChain Tool 改造（调用 Java Service）
- ⏳ LangGraph 工作流集成
- ⏳ 联调测试

### 阶段 3：数据库拆分

- ⏳ Java Service 连接真实数据库
- ⏳ 数据迁移脚本
- ⏳ 工单写入 Agent DB

### 阶段 4：上线部署

- ⏳ Docker 镜像构建
- ⏳ Kubernetes 部署配置
- ⏳ 监控和日志接入

## 🔧 开发指南

### Java Service 开发规范

- **DDD 分层**：Domain → Application → Infrastructure → Interfaces
- **代码风格**：遵循 Google Java Style Guide
- **日志规范**：所有日志必须包含 `trace_id`
- **错误处理**：统一错误码和错误消息格式

### Python Service 开发规范

- **代码风格**：遵循 PEP 8
- **类型注解**：所有函数必须有类型注解
- **异步优先**：使用 `async/await` 处理 I/O 操作
- **工具定义**：使用 `@tool` 装饰器定义 LangChain Tools

### Protobuf 接口规范

- **请求上下文**：所有请求必须包含 `RequestContext`（user_id, trace_id）
- **响应格式**：统一 `code + message + data` 结构
- **错误码**：0=成功，4xx=客户端错误，5xx=服务端错误
- **命名规范**：使用 snake_case

## 📚 文档索引

- [微服务拆分总体规格书](docs/SPEC.md) - 整体架构和拆分方案
- [Java Business Service 规格书](docs/JAVA_BUSINESS_SERVICE_SPEC.md) - Java 服务详细设计
- [Python Agent Service 规格书](docs/PYTHON_AGENT_SERVICE_SPEC.md) - Python 服务详细设计
- [Protobuf 接口定义](proto/business_service.proto) - 服务间接口契约

## 🧪 测试

### Java Service 测试

```bash
cd business-service

# 单元测试
mvn test

# 集成测试
mvn verify

# 测试覆盖率报告
mvn jacoco:report
```

### Python Service 测试

```bash
cd agent-service

# 单元测试
pytest tests/unit

# 集成测试
pytest tests/integration

# 覆盖率报告
pytest --cov=app tests/
```

### gRPC 接口测试

```bash
# 使用 grpcurl 测试 Java Service
grpcurl -plaintext localhost:9090 list

# 查询订单
grpcurl -plaintext -d '{
  "context": {"user_id": "user_123", "trace_id": "test_001"},
  "order_id": "ORD20241201001"
}' localhost:9090 mewhelp.business.OrderService/QueryOrder
```

## 🛠️ 技术栈

### Java Business Service

- **框架**: Spring Boot 3.2+
- **RPC**: gRPC (net.devh:grpc-server-spring-boot-starter)
- **数据库**: MySQL 8.0 + MyBatis
- **日志**: SLF4J + Logback
- **构建**: Maven

### Python Agent Service

- **框架**: FastAPI
- **AI 编排**: LangGraph + LangChain
- **向量数据库**: Milvus
- **关系数据库**: MySQL (SQLAlchemy)
- **RPC**: grpcio + grpcio-tools

## 📊 性能指标

### 目标

- **P99 延迟**: < 500ms (Agent Service)
- **P99 延迟**: < 100ms (Business Service)
- **QPS**: 1000+ (Agent Service)
- **并发连接**: 10000+ (WebSocket)

## 🔐 安全

- **用户身份**: 通过 JWT Token 验证
- **订单归属**: Java 层强制校验订单归属
- **幂等性**: 通过 `request_id` 保证退款等操作幂等
- **日志脱敏**: 敏感信息（手机号、地址）自动脱敏

## 📞 联系方式

- **项目负责人**: [待填写]
- **技术支持**: [待填写]
- **问题反馈**: [GitHub Issues]

## 📄 许可证

[待定]

---

**最后更新**: 2026-09-26
