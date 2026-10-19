# 翁绍成 | 求职意向 - 后端开发实习生 / AI 应用开发实习生

(+86)138-7607-3295 | 1994147063@qq.com | 微信：a13876073295  
**GitHub：** https://github.com/shangxinxiaolin

---

## 教育背景

**燕山大学｜本科｜计算机科学与技术** · 2025.09 - 2029.07

相关课程：数据结构与算法、操作系统、计算机网络、数据库系统

---

## 技术博客

**CSDN：** https://blog.csdn.net/yunxiheyu  
运营个人 **CSDN 博客**，累计吸引 **4000+ 开发者**。

---

## 开源贡献

### Apache Dubbo-Go｜开源贡献者（缺陷定位与复现）

**项目背景：** **Apache 软件基金会顶级项目 Dubbo 的 Go 实现**，提供 RPC 调用、服务发现与治理能力；GitHub **4.9k+ Stars / 1k+ Forks**（2026.10.09 核对）。

**项目地址：** https://github.com/apache/dubbo-go  
**贡献记录：** [Issue #3756](https://github.com/apache/dubbo-go/issues/3756)

- **源码分析与缺陷定位：** 发现引用级显式请求超时 **500ms** 被消费者默认 **3s** 覆盖，追踪 `ReferenceOptions.Refer()` 的 URL 构建路径，定位配置优先级错误，提出引用配置优先、消费者默认值兜底的修复方向。
- **隔离复现与上游反馈：** 使用模拟协议与集群扩展调用实际 `Refer()` 路径，捕获 URL 并断言超时参数，提供无需注册中心或外部服务的复现测试；提交 Issue #3756，获维护者 **Bug** 分类并关联社区修复 PR #3757（由其他贡献者提交）。

---

## 项目经验

### Lumina 灵光平台

**后端开发** · 2025.12 - 至今

**项目描述：** 一套面向知识分享与交流的内容社区后端：用户发布知文，通过 Feed 浏览内容、关注作者并进行点赞收藏；互动变更经事件链路更新内容计数和页面缓存，历史事件支持计数回放重建。采用模块化单体架构，围绕内容浏览、用户关系和互动计数组织业务模块。

**技术栈：** Spring Boot、Spring Security、MySQL、Redis、Kafka、Canal、MyBatis、Docker

**核心实现：**

- **双令牌认证：** 基于 **Spring Security + JWT** 实现访问与续期令牌，使用 Redis 黑名单及版本号控制失效，支持会话续期与强制下线。
- **互动状态与计数聚合：** 使用分片 **Redis Bitmap + Lua** 原子切换点赞/收藏状态，仅在状态变化时发布 Kafka 增量事件，异步聚合到 **SDS 计数快照**；快照缺失时结合位图统计、分布式锁和退避限制重建压力。
- **计数事件回放：** 提供按配置启用的独立 Kafka 回放消费者组，使用 earliest 策略及手动确认，在无已提交位点时从最早保留事件开始消费，通过 Lua 原子累加重建 SDS；恢复范围受事件保留期影响，独立消费者组不等于目标数据隔离。
- **Feed 多级缓存：** 设计 **Caffeine + Redis** 二级缓存及页面反向索引，定位计数变更影响的缓存；个性化状态在返回前通过 Bitmap 叠加，结合滑动窗口热键探测、动态 TTL、单航班回源和随机抖动控制回源压力。
- **关注关系事件同步：** 将关注/取消关注操作与 **Outbox** 事件写入同一 MySQL 事务，经 **Canal → Kafka** 传递关系变更，由消费者更新关系数据、缓存与用户计数，将事务内事件记录和异步处理分离。

### 灵犀客服｜AI Agent 智能客服系统

**后端 / AI 应用开发** · 2026.09 - 至今

**项目地址：** https://github.com/shangxinxiaolin/user-help

**项目描述：** 一套面向电商订单咨询与售后处理的智能客服系统：用户通过自然语言查询订单与物流、咨询政策并申请退款或创建工单；Python Agent 查询业务数据、检索政策并组织回复，用户确认后由 Java 业务服务执行操作。未解决的问题经标准化、人工审核后补入知识库，形成“咨询 → 取证 → 确认 → 执行 → 知识补全”的服务闭环。

**技术栈：** Spring Boot、FastAPI、LangGraph、LangChain、gRPC、MySQL、SQLAlchemy、Milvus、Langfuse

**核心实现：**

- **服务边界与统一入口：** 在 Spring Boot 内集成 **Gateway/BFF 与业务模块**，统一鉴权、限流和 SSE 转发；Python 通过内部 HTTP/SSE 接收请求，通过 **gRPC + Protobuf** 调用 Java，由业务层最终校验归属与操作资格。
- **Agent 编排与可靠执行：** 使用 **LangGraph Workflow + ReAct** 固定检索、订单取证等必经步骤，动态选择业务工具；通过 **interrupt/resume** 绑定用户确认，结合持久化幂等键、输入指纹和数据库唯一约束处理重复提交及参数冲突，超时后按原操作标识查询结果。
- **RAG 混合检索：** 基于 **Milvus** 实现 BGE-M3 向量与 BM25 双路召回，通过 **RRF + Cross-Encoder** 融合重排；配合生成前证据置信度闸、引用溯源与自检，对证据不足的问题拒答或转人工。
- **会话与上下文管理：** 使用 **MySQL + SQLAlchemy** 保存会话消息、SQLite Checkpoint 恢复 Graph 状态，续聊前校验会话归属；通过**原文、规则截短、异步摘要**三层管理历史，控制模型输入预算。
- **数据飞轮与效果评测：** 将低置信度、无效回答和用户负反馈汇入问题池，标准化查重后经人审写回知识库；使用 **Langfuse** 追踪调用与 Token 成本，通过固定案例比较检索策略、校准证据阈值，并以模型/RPC 替身测试业务失败路径。

---

## 技能清单

- **编程语言：** Java、Python
- **后端框架：** Spring Boot、Spring Security、MyBatis、FastAPI、LangChain、LangGraph
- **中间件：** Redis、Kafka、Canal、gRPC、Protobuf
- **数据库：** MySQL、SQLite
- **AI 应用：** Agent Workflow、Function Calling、RAG、会话上下文、Checkpoint、可观测性设计
- **工程工具：** Git、Maven、Docker、Linux、pytest
