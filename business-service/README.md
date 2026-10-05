# Business Service - Java 后端服务

本服务按业务模块组织代码，包根为 `com.shangui.userhelp`，目录风格参考 `zhiguang` 项目。

## 项目信息

- **项目名称**: MewHelp Business Service
- **版本**: 1.0.0-SNAPSHOT
- **开发环境基线**: JDK 21；POM 同时保留 compiler source/target=17，构建配置口径尚待单独统一，本文不宣称产物版本已验证。
- **Spring Boot 版本**: 3.2.0
- **构建工具**: Maven

## 技术栈

### 核心框架

| 技术 | 版本 | 说明 |
|------|------|------|
| Spring Boot | 3.2.0 | 应用框架 |
| gRPC Server | 1.60.1 | RPC 服务端 |
| gRPC Spring Boot Starter | 3.1.0.RELEASE | gRPC 与 Spring Boot 集成 |
| Protobuf | 3.25.1 | 接口定义和序列化 |
| 数据访问 | Mock Mapper | 当前没有 MyBatis、MySQL Connector 或 HikariCP 的直接依赖；数据库阶段再接入 |
| Lombok | Latest | 简化 Java 代码 |

### 监控和日志

| 技术 | 说明 |
|------|------|
| Actuator / Prometheus | 目标能力；当前 POM 未声明相应依赖，不能据 management 配置宣称端点可用 |
| Logback | 日志框架 |
| SLF4J | 日志接口 |

### 测试框架

| 技术 | 说明 |
|------|------|
| JUnit 5 | 单元测试框架 |
| Mockito | Mock 框架 |
| AssertJ | 流式断言库 |
| gRPC 集成测试 | 待补充，当前 POM 未声明 grpc-testing |
| JaCoCo | 测试覆盖率 |

## 项目结构

```
src/main/java/com/shangui/userhelp/
├── UserHelpApplication.java            # 唯一启动类
├── common/                             # 公共错误和 Web 处理
├── business/api/                       # 本地调试 HTTP 接口
├── order/                              # 订单模块
│   ├── api/
│   ├── domain/
│   ├── mapper/
│   └── service/
│       └── impl/
├── logistics/                          # 物流模块
├── aftersales/                         # 售后模块
├── refund/                             # 退款模块
├── ticket/                             # 工单模块
└── rpc/                                # gRPC 适配层

src/main/proto/                        # Protobuf 定义
src/main/resources/
└── application.yml                    # 当前唯一资源配置；日志 XML 与 MyBatis Mapper XML 尚未建立
```

## 快速开始

### 环境要求

- JDK 21（当前开发基线；compiler 的 17/21 混合配置需要单独核实）
- Maven 3.8+
- MySQL 8.0+ (可选，Mock 阶段不需要)

### 构建项目

```bash
# 清理并编译
mvn clean compile

# 运行测试
mvn test

# 打包
mvn clean package

# 跳过测试打包
mvn clean package -DskipTests
```

### 启动服务

```bash
# 开发模式启动
mvn spring-boot:run

# 或者运行打包后的 jar
java -jar target/business-service-1.0.0-SNAPSHOT.jar
```

### 验证服务

```bash
# 检查 gRPC 端口
netstat -an | findstr 9090

# 检查业务调试接口（当前未接入 Actuator）
curl.exe -H "X-User-Id: u1" http://localhost:8080/api/business/orders/1001

# 使用 grpcurl 测试（需要先安装）
grpcurl -plaintext localhost:9090 list
```

## 配置说明

### application.yml 关键配置

```yaml
# gRPC 端口
grpc:
  server:
    port: 9090

# Mock 数据开关
app:
  mock:
    enabled: true  # 当前只是配置值，Mock Mapper 未提供 false 切换到真实数据库的实现
```

## 依赖管理

### 添加新依赖

在 `pom.xml` 中添加：

```xml
<dependency>
    <groupId>group-id</groupId>
    <artifactId>artifact-id</artifactId>
    <version>version</version>
</dependency>
```

### 更新依赖

```bash
# 查看可更新的依赖
mvn versions:display-dependency-updates

# 更新依赖版本
mvn versions:use-latest-releases
```

## 开发规范

### 代码风格

- 遵循 Google Java Style Guide
- 使用 Lombok 简化代码
- 新增公开方法建议说明契约；当前没有全面遵循此要求，不能视为已验收规范。

### 日志规范

```java
// 使用 SLF4J + Lombok
@Slf4j
public class MyService {
    public void doSomething(String traceId, String userId) {
        // 必须包含 traceId
        log.info("[{}] 处理请求：userId={}", traceId, userId);
        
        try {
            // 业务逻辑
        } catch (Exception e) {
            log.error("[{}] 处理失败", traceId, e);
        }
    }
}
```

### 异常处理

```java
// 使用自定义业务异常
throw new BusinessException(ErrorCode.NOT_FOUND, "没有找到您的这笔订单");
throw new BusinessException(ErrorCode.FORBIDDEN, "没有找到您的这笔订单");
throw new BusinessException(ErrorCode.BAD_REQUEST, "参数错误");
```

## 测试

### 单元测试

```bash
# 运行所有测试
mvn test

# 运行指定测试类
mvn test -Dtest=OrderServiceTest

# 运行指定测试方法
mvn test "-Dtest=OrderServiceTest"
```

### 测试覆盖率

```bash
# 生成覆盖率报告
mvn clean test jacoco:report

# 查看报告
open target/site/jacoco/index.html
```

## 监控

### Actuator 端点

当前 POM 未接入 Actuator 与 Prometheus registry；`application.yml` 中的 management 段不能单独启用端点。健康与指标端点待依赖、配置和实际请求验证完成后再记录为可用。

### 日志文件

- 应用日志: `logs/business-service.log`
- 独立错误日志文件尚未配置；没有 `logback-spring.xml`。本轮未运行验证日志文件输出。

## 常见问题

### Q: Maven 构建失败，提示找不到 protoc？

A: 需要安装 protobuf 编译器，或者让 Maven 自动下载（已配置）。

### Q: gRPC 启动失败，端口被占用？

A: 修改 `application.yml` 中的 `grpc.server.port` 配置。

### Q: 连接 MySQL 失败？

A: 当前 Java 使用 Mock Mapper，没有数据源配置和数据库驱动。此问题仅在后续真实数据库阶段适用；Java 不能连接或直接写 Python 的 `lingxi_agent` 库。

## 下一步

Mock 业务接口已实现（订单、物流、售后、退款、工单及幂等）。后续：

1. 与 Python Agent Service 联调（B 阶段：Python 工具 → gRPC → Java 查询订单）。
2. 退款/工单从进程内存持久化到 Business DB（C 阶段）。
3. 接入 MyBatis + MySQL，替换 Mock Mapper。
4. 服务治理与性能优化（后续阶段）。

## 相关文档

- [Java 规格书](docs/JAVA_BUSINESS_SERVICE_SPEC.md)
- [项目总览](../README.md)
- [Protobuf 定义（实际契约）](src/main/proto/business_service.proto)

---

**维护者**: MewHelp Team  
**最后更新**: 2026-10-06
