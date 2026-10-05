# Java Business Service 初始化记录（已归档）

历史日期：2026-09-26；核对日期：2026-10-06。

本文件不作为当前开发清单。早期记录使用过 DDD 四层目录、旧包名和计划中的数据库/监控依赖，已经被当前业务模块结构取代；旧“全部完成”结论不适用于当前项目。

## 当前代码基线

- 启动类：`com.shangui.userhelp.UserHelpApplication`。
- 业务模块：order、logistics、aftersales、refund、ticket，包含 domain、mapper、service 和 gRPC Endpoint。
- 实际契约：[business_service.proto](src/main/proto/business_service.proto)，已有 Java 代码生成配置。
- 数据来源：Mock Mapper；退款和工单幂等保存在进程内存，重启后不保留。
- 资源目录当前只有 `application.yml`，没有日志 XML 或 MyBatis Mapper XML。
- POM 未声明 MyBatis、MySQL Connector、Actuator、Prometheus registry 或 grpc-testing；配置文本不能代表功能已接入。
- 开发基线 JDK 21，但 POM 的 java.version=21 与 compiler source/target=17 并存，构建目标尚需单独核实。

以上是静态核对结果，本轮未运行 Maven，不将历史记录作为当前编译、启动或测试成功的证据。

## 后续入口

先完成 Python A 阶段接线，然后进行 Mock QueryOrder 联调；数据库、持久化幂等和退款状态机在 C 阶段经确认后实施。

- [当前 Java 使用说明](README.md)
- [Java 服务规格](docs/JAVA_BUSINESS_SERVICE_SPEC.md)
- [当前依赖核对](DEPENDENCY_CHECKLIST.md)
- [总规格与主实施顺序](../docs/SPEC.md)
