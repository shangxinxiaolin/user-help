# Java Business Service 依赖核对

核对日期：2026-10-06。依据当前 `pom.xml` 与资源文件；不是运行验证报告。

## 当前明确声明的依赖

- Spring Boot parent 3.2.0、starter、starter-web。
- grpc-server-spring-boot-starter 3.1.0.RELEASE。
- protobuf-java 3.25.1。
- grpc-protobuf、grpc-stub、grpc-netty-shaded 1.60.1。
- Tomcat annotations-api 6.0.53。
- Lombok、starter-validation、starter-test。

starter-test 的传递依赖用于 JUnit/Mockito/AssertJ 测试；不将传递依赖写成项目单独声明的依赖数量。

## 当前未声明的目标依赖

MyBatis、MySQL Connector、Actuator、Prometheus registry、grpc-testing 均未声明。当前业务使用内存 Mock，包括工单，不要求 MySQL。未来 Business DB 与 Python Agent DB 必须保持服务所有权隔离。

`application.yml` 的 management 与 mock.enabled 配置，不代表监控端点已启用或已实现切换到真实数据库。

## 构建配置

- 插件包含 Spring Boot、Protobuf 0.6.1、Compiler、Surefire、JaCoCo 0.8.11；OS 检测扩展为 1.7.1。
- 开发环境基线为 JDK 21；POM java.version=21 与 compiler source/target=17 并存，需要单独确认实际目标，本文不修改构建文件。
- Proto 已存在；下一步不是重新创建契约，而是冻结业务错误映射、生成 Python Stub 并联调。
- 唯一资源配置为 `src/main/resources/application.yml`；没有 logback-spring.xml 或 Mapper XML。

## 核验命令

从 `business-service` 执行，运行结果需单独记录：

```powershell
mvn dependency:tree
mvn clean test
mvn package
```

## 文档入口

- [Java README](README.md)
- [Java 规格](docs/JAVA_BUSINESS_SERVICE_SPEC.md)
- [历史初始化记录](SETUP_COMPLETE.md)
- [总规格与主实施顺序](../docs/SPEC.md)
