# MewHelp 微服务拆分规格书

> 本文档描述整体拆分方向。Java 业务服务的可执行细节以同目录的
> `JAVA_BUSINESS_SERVICE_SPEC.md` 和 `business-service/src/main/proto/business_service.proto` 为准。

## 文档目的

本文档为 MewHelp 电商智能客服系统的微服务拆分提供详细规格说明，目标是将当前单体 Python 应用拆分为：

- **Python Agent Service**：负责对话编排、意图识别、工具调用、知识库检索
- **Java Business Service**：负责订单、物流、售后、退款、工单等核心业务逻辑

本文档可供其他 agent 或开发人员阅读并执行实施。

---

## 一、当前项目现状分析

### 1.1 技术栈

| 组件 | 技术 |
|---|---|
| Web 框架 | FastAPI |
| 工作流编排 | LangGraph |
| 模型调用 | LangChain + OpenAI SDK |
| 关系数据库 | MySQL + SQLAlchemy |
| 向量数据库 | Milvus |
| 外部工具协议 | MCP (Model Context Protocol) |
| 前端 | 静态 HTML + JavaScript |

### 1.2 当前目录结构

```text
MEWHELP python/
├── app/
│   ├── api/          # HTTP 接口层
│   ├── graph/        # LangGraph 工作流
│   ├── core/         # 核心能力（LLM、意图、检索、摘要）
│   ├── tools/        # 工具注册、执行引擎、MCP 客户端
│   ├── kb/           # 知识库管理
│   ├── db/           # 数据模型和仓储
│   ├── static/       # 前端页面
│   └── main.py       # FastAPI 应用入口
├── mcp_servers/      # 业务 MCP Server（物流、售后）
├── scripts/          # 离线脚本
├── tests/            # 单元测试
├── sql/              # 数据库建表和种子数据
├── data/             # 知识库文档、评估集
└── docker-compose.yml
```

### 1.3 核心请求链路

```text
用户请求
  ↓
/api/chat 或 /api/agent
  ↓
app/graph/runtime.stream_turn() 或 run_turn()
  ↓
LangGraph 工作流
  ├─ resolve_reference      # 指代消解
  ├─ classify_intent        # 意图识别
  ├─ route_by_intent        # 意图分流
  │    ├─ knowledge         → retrieve_knowledge → confidence_check → main_agent
  │    ├─ refund_flow       → fetch_order → retrieve_policy → main_agent
  │    ├─ business          → main_agent
  │    ├─ escalate          → complaint_reply
  │    └─ fallback_script   → script_reply
  ├─ main_agent             # ReAct 工具循环
  ├─ agent_tools            # 工具执行
  └─ log                    # 日志节点
  ↓
返回答案、工具调用轨迹、引用、中断
```

### 1.4 当前业务能力分布

#### 内置工具（Python）

位置：`app/tools/builtin/`

| 工具 | 位置 | 职责 |
|---|---|---|
| `query_order` | `orders.py` | 查询订单快照 |
| `query_faq` | `faq.py` | 查询 FAQ |
| `submit_refund` | `refunds.py` | 提交退款（被拦截成前端表单） |
| `create_ticket` | `tickets.py` | 创建工单 |

#### MCP 工具（独立进程）

位置：`mcp_servers/`

| 工具 | Server | 端口 | 职责 |
|---|---|---|---|
| `query_logistics` | `logistics_server.py` | 8101 | 查询物流 |
| `query_warranty` | `aftersales_server.py` | 8102 | 查询保修 |
| `query_return_status` | `aftersales_server.py` | 8102 | 查询退货进度 |

#### 业务数据函数

位置：`app/tools/business.py`

| 函数 | 职责 |
|---|---|
| `order_snapshot(order_id)` | 生成订单快照（mock） |
| `owns_order(user_id, order_id)` | 订单归属校验 |
| `list_user_orders(user_id)` | 列出用户订单 |

#### 数据库表

位置：`app/db/models.py`

| 表 | 用途 | 归属服务 |
|---|---|---|
| `conversations` | 会话 | Agent |
| `messages` | 消息 | Agent |
| `faq` | FAQ | Knowledge |
| `tickets` | 工单 | Business |
| `knowledge_chunks` | 知识块 | Knowledge |
| `qa_extraction_staging` | QA 暂存 | Knowledge |
| `tool_audit_logs` | 工具审计 | Agent |
| `low_confidence_questions` | 低置信度问题池 | Agent |
| `review_queue` | 飞轮待审队列 | Knowledge |
| `eval_runs` | 评估记录 | Agent |
| `faith_cases` | 忠实度个案 | Knowledge |
| `topic_classifications` | 主题分类 | Agent |

### 1.5 核心设计模块

#### 1.5.1 置信度闸（Evidence Confidence Gate）

**位置**：`app/core/confidence.py`、`app/graph/nodes.py:retrieve_knowledge`

**原理**：在知识库检索后、模型生成答案前，通过四个信号量化证据质量，拒绝低质量证据。

**四信号加权模型**：

```python
score = W_TOP1 * top1_score        # 0.5：精排 Top1 得分
      + W_VALID * valid_count / 3  # 0.2：有效证据数（≥0.3分的条数）
      + W_MARGIN * margin           # 0.2：Top1 与 Top2 分差
      + W_KEY * key_clause_hit      # 0.1：前3条是否命中关键条款
```

**触发条件**：

```text
检索完成
  ↓
compute_evidence_confidence()
  ↓
score < threshold (默认 0.26)
  ↓
fallback_reply + 落入低置信度问题池
```

**拆分归属**：Agent Service（知识检索与置信度判断不涉及业务数据）

---

#### 1.5.2 数据飞轮（Knowledge Flywheel）

**位置**：`app/core/flywheel.py`、`scripts/flywheel_pipeline.py`

**目的**：把低置信度问题池中的问题标准化、去重、生成 AI 建议答案，形成待审队列，人工审核后写回知识库。

**流程**：

```text
低置信度问题池（low_confidence_questions）
  ↓
批处理扫描未归并的问题（matched_review_id IS NULL）
  ↓
逐条调用 LLM 标准化 + 查重
  ├─ 输入：raw_question + 现有待审队列候选
  ├─ 输出：normalized_question + matched_question_id + ai_suggested_answer
  ↓
命中已有候选
  ├─ 是 → increment_occurrence（累加出现次数）
  └─ 否 → insert_review_item（新建待审条目）
  ↓
回写 matched_review_id
  ↓
人工审核（/review 页面）
  ├─ 通过 → 写入 knowledge_chunks + 向量化
  └─ 驳回 → 标记为终审，不再复活
```

**关键特性**：

- 串行逐条处理（同批次同义问题可归并）
- 幂等可重跑（游标 = matched_review_id IS NULL）
- 候选集限 200 条（防止上下文过长）
- 解析失败跳过并告警（下轮重试）

**运行方式**：

```bash
make flywheel              # 手动运行
cron: */30 * * * *         # 定时批处理
```

**拆分归属**：Agent Service（知识库管理不涉及业务系统）

---

#### 1.5.3 对话挖知识（Conversation Mining）

**位置**：`app/kb/mining.py`、`scripts/mine_knowledge.py`

**目的**：从历史对话中提取可复用的 QA 对，补充知识库。

**流程**：

```text
历史会话（conversations + messages）
  ↓
加载 user/assistant 消息拼成对话文本
  ↓
分批调用 LLM 抽取 QA 对
  ├─ 输入：对话文本（多条会话批处理）
  ├─ 输出：questions[] + answers[]（并列数组一一对应）
  ↓
写入 qa_extraction_staging（status=extracted）
  ↓
整体去重（本批内 + 对已有知识库）
  ├─ 指纹：questions + answer 组合
  ├─ kept：去重后保留
  └─ discarded：重复丢弃
  ↓
人工审核（/kb 页面「对话挖知识」卡片）
  ├─ 采纳 → insert_knowledge_chunk + 向量化
  └─ 弃用 → 标记 discarded
```

**为什么要人工审核**：

> 客服对话中的回答可能只对特定订单成立，可能包含具体订单号和地址，也可能只是「稍等我帮您看看」。这种内容不能直接进知识库，必须人工筛选。

**运行方式**：

```bash
make kb-mine
```

**拆分归属**：Agent Service

---

#### 1.5.4 RAG 评估体系

**位置**：`scripts/eval_ch04.py`、`tests/data/eval_ch04.jsonl`、`app/api/rageval.py`

**目的**：对比四种检索策略（vector、bm25、hybrid、hybrid_rerank）的召回率、忠实度、覆盖率。

**评估集格式**：

```json
{
  "id": "eval-001",
  "question": "运费怎么算",
  "ground_truth_chunk_ids": [12, 34],
  "key_points": ["满99包邮", "新疆西藏除外"]
}
```

**评估指标**：

| 指标 | 说明 |
|---|---|
| 召回率 | ground_truth_chunk_ids 被召回的比例 |
| 覆盖率 | key_points 在答案中被覆盖的比例 |
| 忠实度 | 答案是否基于证据（LLM Judge 裁判） |

**忠实度裁判流程**：

```text
证据 + 答案
  ↓
LLM Judge（temperature=0）
  ├─ 角色：严格裁判
  ├─ 任务：判断答案是否忠实于证据
  ├─ 输出：{faithful: bool, reason: str}
  ↓
个案台账（faith_cases）
  ├─ 记录编造答案
  ├─ 跨轮累计 seen_count
  └─ 人工标记处置状态
```

**运行方式**：

```bash
make eval-rag              # 跑四策略评估
make eval-check            # 验证评估集自洽性
make judge-check           # 忠实度裁判回归测试
```

**拆分归属**：Agent Service（评估知识检索质量）

---

#### 1.5.5 上下文管理（滑窗 + 摘要 + 前缀缓存）

**位置**：`app/core/memory.py`、`app/core/summarizer.py`、`app/graph/nodes.py:_agent_messages`

**问题**：对话历史无限累积会撑爆上下文窗口。

**解决方案**：

```text
早期轮次
  ↓
后台异步摘要（conversations.summary）
  ↓
最近轮次
  ↓
滑窗保留原文（context_window_turns=8）
  ↓
发送给模型时组合
  ├─ SystemMessage（人设 + 工具 schema）
  ├─ 摘要行（早期轮次压缩）
  ├─ 滑窗原文（最近轮次）
  └─ 本轮材料（证据 + 订单数据）
```

**摘要触发**：

```text
每轮对话结束
  ↓
检查距上次摘要新增消息数
  ↓
≥ 30 条
  ↓
后台异步生成摘要
  ↓
更新 conversations.summary + summary_upto_msg_id
```

**前缀缓存优化**：

```text
SystemMessage + 工具 schema
  ↓
保持逐字不变（不要把摘要塞进 system）
  ↓
上游缓存命中（cache_read token）
```

**拆分归属**：Agent Service

---

#### 1.5.6 主题分类器（可选模块）

**位置**：`scripts/ch10/`、`app/core/taxonomy.py`

**目的**：旁路批量归类问题，统计各主题分布，辅助意图识别。

**流程**：

```text
低置信度问题池
  ↓
批量调用分类器推理服务（:8110 ONNX）
  ↓
写入 topic_classifications
  ↓
前端展示主题分布（/topics 页面）
```

**训练流程**：

```bash
make ch10-corpus     # 生成语料
make ch10-dataset    # 划分训练/验证/测试集
make ch10-train      # RoBERTa-wwm-ext 全参微调
make ch10-export     # 导出 ONNX
make ch10-eval       # 测试集评估
```

**推理服务**：

```bash
make classifier-up   # 启动 :8110
make classify-pool   # 批量归类
```

**拆分归属**：Agent Service（主题分类属于意图理解能力）

---

#### 1.5.7 工具审计（Tool Audit）

**位置**：`app/tools/engine.py`、`app/db/models.py:ToolAuditLog`

**目的**：记录所有工具调用的执行过程、结果、耗时、重试次数。

**记录内容**：

| 字段 | 说明 |
|---|---|
| conversation_id | 会话 ID |
| tool_call_id | 工具调用 ID |
| tool_name | 工具名称 |
| tool_source | builtin / mcp |
| mcp_server | MCP Server 名称 |
| arguments | 调用参数 |
| result_summary | 结果摘要（截断 500 字） |
| status | 成功 / 失败 / 超时 / 校验拦下 / 权限拒绝 |
| error_message | 错误信息 |
| retry_count | 重试次数 |
| duration_ms | 执行耗时 |

**日志输出**：

```text
INFO:app.core.observability:tool_run conv=123 tool=query_order source=builtin server=- status=成功 retry=0 duration_ms=45
```

**拆分后处理**：

- Agent Service 仍然记录工具调用审计
- 调用 Business Service RPC 时记录：
  - 请求参数
  - RPC 延迟
  - 业务错误码
  - 重试次数

**拆分归属**：Agent Service（工具编排层审计）

---

#### 1.5.8 可观测性（Langfuse + 成本统计）

**位置**：`app/core/observability.py`、`scripts/cost_by_intent.py`

**Langfuse 集成**：

```text
app/main.py: lifespan
  ↓
runtime.init_graph()
  ↓
attach_observability(graph)
  ↓
所有模型调用自动 trace
  ├─ trace_id = conversation_id
  ├─ session_id = conversation_id
  └─ metadata = {intent, intent_confidence}
```

**成本统计**：

```bash
make cost-report --days=7
```

输出：

| 意图 | 调用次数 | Input Token | Output Token | 总成本 |
|---|---|---|---|---|
| 物流 | 120 | 15000 | 2400 | $0.05 |
| 退款 | 80 | 12000 | 1800 | $0.04 |
| FAQ | 200 | 25000 | 3500 | $0.08 |

**拆分归属**：Agent Service（观测模型调用）

---

## 二、拆分目标架构

### 2.1 服务拆分方案

```text
┌──────────────────────────────────────────────────┐
│              前端 / API Gateway                   │
└─────────────────┬────────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
┌─────────────────┐        gRPC        ┌─────────────────┐
│ Agent Service   │ ─────────────────▶ │ Business Service│
│   (Python)      │                    │     (Java)      │
│                 │                    │                 │
│ - LangGraph     │                    │ - order/        │
│ - 意图识别      │                    │ - logistics/    │
│ - 工具编排      │                    │ - aftersales/  │
│ - 知识检索      │                    │ - refund/       │
│ - 上下文管理    │                    │ - ticket/       │
│ - SSE 流式输出  │                    │ - 业务校验      │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│ Agent DB/Milvus │                    │ Mock Mapper     │
│ 会话/知识/审计  │                    │ 后续可替换MyBatis│
└─────────────────┘                    └─────────────────┘
```

### 2.2 技术选型

| 组件 | Agent Service | Business Service |
|---|---|---|
| 语言 | Python 3.12+ | Java 17+ |
| Web 框架 | FastAPI | Spring Boot |
| 工作流 | LangGraph | - |
| 数据库 | MySQL | 当前无数据库，后续 MyBatis |
| 数据访问 | SQLAlchemy | Mapper 接口 + Mock 实现 |
| RPC | gRPC Client | gRPC Server |
| 向量库 | Milvus | - |
| 容器化 | Docker | Docker |

### 2.3 为什么这样拆

| 关注点 | 理由 |
|---|---|
| **语言边界** | Agent 编排和 LLM 调用生态在 Python；订单、物流、退款等业务逻辑适合 Java |
| **团队边界** | AI 团队维护 Agent Service，业务团队维护 Business Service |
| **性能边界** | Agent 需要流式输出、长连接；业务服务需要高吞吐、事务保证 |
| **扩展边界** | Agent 无状态扩展，业务服务按业务线扩展 |
| **数据边界** | Agent 拥有对话和工作流状态；Business 拥有订单、物流、工单数据 |

---

## 三、服务职责划分

### 3.1 Agent Service 职责

**核心职责**：理解用户意图，编排工具调用，组织知识证据，生成自然语言回答。

| 能力 | 描述 |
|---|---|
| 意图识别 | 用户问题归类为订单、物流、退款、FAQ、投诉、闲聊等 |
| 指代消解 | 把"那个订单"解析成完整订单号 |
| 知识检索 | 混合检索（向量+BM25）+ 重排 + 证据组织 |
| 置信度判断 | 检索证据是否足够支撑回答 |
| 工具编排 | 决定调用哪些业务能力，如何组合 |
| 上下文管理 | 滑窗、摘要、前缀缓存 |
| 流式输出 | SSE 流式返回回答增量 |
| 中断恢复 | interrupt/resume 机制 |
| 审计日志 | 记录工具调用、模型消耗、决策轨迹 |

**保留模块**：

```text
app/graph/
app/core/
app/tools/registry.py
app/tools/engine.py (改造为 RPC Client)
app/kb/
app/api/chat.py
app/api/agent.py
```

**保留数据表**：

```text
conversations
messages
tool_audit_logs
low_confidence_questions
review_queue
eval_runs
knowledge_chunks
qa_extraction_staging
faith_cases
topic_classifications
```

### 3.2 Business Service 职责

**核心职责**：执行业务逻辑，校验权限，保证数据一致性。

| 能力 | 描述 |
|---|---|
| 订单查询 | 根据订单号查询订单状态、金额、商品、物流单号 |
| 订单归属校验 | 验证订单是否属于当前用户 |
| 物流查询 | 根据物流单号查询物流状态和轨迹 |
| 售后查询 | 查询保修状态、退货进度 |
| 退款流程 | 校验退款条件、创建退款单 |
| 工单系统 | 创建工单、更新工单状态 |
| 权限控制 | 用户身份校验、操作权限判断 |
| 业务规则 | 退款条件、工单类型、状态流转 |

**Java 模块组织方式**：

```text
business-service/src/main/java/com/shangui/userhelp/
├── order/{api,domain,mapper,service}
├── logistics/{api,domain,mapper,service}
├── aftersales/{api,domain,mapper,service}
├── refund/{api,domain,mapper,service}
├── ticket/{api,domain,mapper,service}
├── common/{error,web}
└── rpc/
```

业务迁移映射：

```text
app/tools/builtin/orders.py       → order/service + OrderGrpcEndpoint
app/tools/builtin/refunds.py      → refund/service + RefundGrpcEndpoint
app/tools/builtin/tickets.py      → ticket/service + TicketGrpcEndpoint
app/tools/business.py             → order/mapper/MockOrderMapper
mcp_servers/logistics_server.py   → logistics/mapper/MockLogisticsMapper
mcp_servers/aftersales_server.py  → aftersales/mapper/MockAftersalesMapper
```

当前不创建业务数据库表。`Mock*Mapper` 实现稳定的演示数据和进程内幂等；真实数据库阶段再增加 MyBatis Mapper。

---

## 四、RPC 接口契约

### 4.1 通信协议

- **协议**：gRPC
- **序列化**：Protobuf
- **传输**：HTTP/2
- **认证**：内部服务间使用 mTLS 或共享密钥

### 4.2 订单服务接口

#### QueryOrder

**请求**：

```protobuf
message QueryOrderRequest {
  string user_id = 1;           // 用户 ID（从 Agent 上下文注入，不可信任模型填写）
  string order_id = 2;          // 订单号（模型抽取）
  string conversation_id = 3;   // 会话 ID（用于审计）
}
```

**响应**：

```protobuf
message QueryOrderResponse {
  bool success = 1;
  string error_code = 2;        // ORDER_NOT_FOUND / ORDER_NOT_OWNED / INTERNAL_ERROR
  string message = 3;
  OrderSnapshot order = 4;
}

message OrderSnapshot {
  string order_id = 1;
  string status = 2;            // 待付款 / 已付款 / 已发货 / 已签收
  int32 amount = 3;
  string created_at = 4;
  string product = 5;
  string tracking_no = 6;       // 物流单号
}
```

**业务规则**：

1. 必须校验 `user_id` 和 `order_id` 的归属关系
2. 订单不存在返回 `ORDER_NOT_FOUND`
3. 订单不属于该用户返回 `ORDER_NOT_OWNED`（不泄露订单存在性）
4. 数据库异常返回 `INTERNAL_ERROR`

#### ListUserOrders

**请求**：

```protobuf
message ListUserOrdersRequest {
  string user_id = 1;
  string conversation_id = 2;
}
```

**响应**：

```protobuf
message ListUserOrdersResponse {
  bool success = 1;
  string error_code = 2;
  repeated OrderBrief orders = 3;
}

message OrderBrief {
  string order_id = 1;
  string product = 2;
  string status = 3;
  int32 amount = 4;
}
```

### 4.3 物流服务接口

#### QueryLogistics

**请求**：

```protobuf
message QueryLogisticsRequest {
  string user_id = 1;
  string tracking_no = 2;
  string conversation_id = 3;
}
```

**响应**：

```protobuf
message QueryLogisticsResponse {
  bool success = 1;
  string error_code = 2;
  LogisticsInfo info = 3;
}

message LogisticsInfo {
  string tracking_no = 1;
  string status = 2;            // 已揽件 / 运输中 / 派送中 / 已签收
  string current_city = 3;
  repeated string trace = 4;
}
```

### 4.4 售后服务接口

#### QueryWarranty

**请求**：

```protobuf
message QueryWarrantyRequest {
  string user_id = 1;
  string order_id = 2;
  string conversation_id = 3;
}
```

**响应**：

```protobuf
message QueryWarrantyResponse {
  bool success = 1;
  string error_code = 2;
  WarrantyInfo info = 3;
}

message WarrantyInfo {
  string order_id = 1;
  string warranty_status = 2;   // 在保 / 已过保
  string warranty_until = 3;
}
```

#### QueryReturnStatus

**请求**：

```protobuf
message QueryReturnStatusRequest {
  string user_id = 1;
  string order_id = 2;
  string conversation_id = 3;
}
```

**响应**：

```protobuf
message QueryReturnStatusResponse {
  bool success = 1;
  string error_code = 2;
  ReturnInfo info = 3;
}

message ReturnInfo {
  string order_id = 1;
  string return_status = 2;     // 审核中 / 退货中 / 已退款 / 无退货记录
  string updated_at = 3;
}
```

### 4.5 退款服务接口

#### ValidateRefund

**请求**：

```protobuf
message ValidateRefundRequest {
  string user_id = 1;
  string order_id = 2;
  string conversation_id = 3;
}
```

**响应**：

```protobuf
message ValidateRefundResponse {
  bool success = 1;
  string error_code = 2;        // ORDER_NOT_FOUND / REFUND_NOT_ALLOWED / ALREADY_REFUNDED
  string message = 3;
  bool refundable = 4;
  string reason = 5;            // 不可退款时的原因
}
```

#### SubmitRefund

**请求**：

```protobuf
message SubmitRefundRequest {
  string user_id = 1;
  string order_id = 2;
  string reason = 3;
  string conversation_id = 4;
  string idempotency_key = 5;   // 幂等键
}
```

**响应**：

```protobuf
message SubmitRefundResponse {
  bool success = 1;
  string error_code = 2;
  string refund_id = 3;
  string message = 4;
}
```

**业务规则**：

1. 必须再次校验订单归属
2. 必须校验订单状态是否允许退款
3. 必须检查幂等键，防止重复提交
4. 退款记录必须写入业务数据库

### 4.6 工单服务接口

#### CreateTicket

**请求**：

```protobuf
message CreateTicketRequest {
  string user_id = 1;
  int64 conversation_id = 2;
  string description = 3;
  string ticket_type = 4;       // 售后 / 投诉 / 咨询 / 退款
  string idempotency_key = 5;
}
```

**响应**：

```protobuf
message CreateTicketResponse {
  bool success = 1;
  string error_code = 2;
  string ticket_no = 3;
  string message = 4;
}
```

---

## 五、数据库拆分方案

### 5.1 Agent Service 数据库

**Schema**：`agent_db`

| 表 | 用途 |
|---|---|
| `conversations` | 会话记录 |
| `messages` | 对话消息 |
| `tool_audit_logs` | 工具调用审计 |
| `low_confidence_questions` | 低置信度问题池 |
| `review_queue` | 知识飞轮待审队列 |
| `eval_runs` | 评估记录 |
| `knowledge_chunks` | 知识块（暂时保留，后续可独立成 Knowledge Service） |
| `qa_extraction_staging` | QA 暂存 |
| `faith_cases` | 忠实度个案 |
| `topic_classifications` | 主题分类 |

**外部依赖**：

- Milvus：知识向量检索
- LangGraph Checkpointer：`data/ch05_checkpoints.sqlite`

### 5.2 Business Service 数据库

**当前阶段**：无 Business DB，业务数据由 Mock Mapper 提供。

**后续阶段**：需要真实业务数据时再创建 `business_db`。

| 表 | 用途 |
|---|---|
| `orders` | 订单主表 |
| `order_items` | 订单明细 |
| `logistics` | 物流信息 |
| `refunds` | 退款记录 |
| `tickets` | 工单 |
| `aftersales_records` | 售后记录 |
| `users` | 用户信息（如需要） |

**注意**：

- 当前项目中的 `tickets` 仍由 Python 原项目维护；Java Mock 阶段不写 Agent DB，避免跨服务直接写库。
- 后续确定工单数据归属后，应通过业务服务自己的 MyBatis Mapper 持久化。
- Agent Service 不应直接访问 Business DB。

### 5.3 数据迁移策略

#### 阶段一：保持共享数据库

- Agent Service 和 Business Service 共享同一个 MySQL 实例
- 使用不同的数据库用户
- Agent 只能读写 `agent_db`，Business 只能读写 `business_db`
- 通过数据库权限控制强制边界

#### 阶段二：物理隔离

- Agent DB 和 Business DB 部署到不同的 MySQL 实例
- 通过 RPC 完全隔离数据访问
- 考虑使用分布式事务或 Saga 模式处理跨服务事务

---

## 六、关键流程设计

### 6.1 订单查询流程

```text
用户："订单 1001 的物流到哪了"
  ↓
Agent Service
  ├─ 意图识别：物流
  ├─ 指代消解：1001
  ├─ 模型选择工具：query_order
  ↓
Agent Service 调用 gRPC
  ├─ user_id = "u1" (从上下文注入)
  ├─ order_id = "1001" (模型抽取)
  ├─ conversation_id = 123
  ↓
Business Service
  ├─ 校验 user_id 和 order_id 归属
  ├─ 查询订单数据库
  ├─ 返回 OrderSnapshot
  ↓
Agent Service
  ├─ 提取 tracking_no
  ├─ 模型再次选择工具：query_logistics
  ↓
Agent Service 调用 gRPC
  ├─ user_id = "u1"
  ├─ tracking_no = "SF123456789"
  ↓
Business Service
  ├─ 查询物流数据库
  ├─ 返回 LogisticsInfo
  ↓
Agent Service
  ├─ 模型生成自然语言回答
  ├─ 流式返回给前端
```

### 6.2 退款确认流程

```text
用户："我要退订单 1001"
  ↓
Agent Service
  ├─ 意图识别：退款退货
  ├─ 路由到 refund_flow
  ├─ fetch_order 节点
  ↓
Agent Service 调用 gRPC: QueryOrder
  ↓
Business Service 返回订单快照
  ↓
Agent Service
  ├─ retrieve_policy 节点（知识库检索退款政策）
  ├─ main_agent 节点判断是否可退
  ├─ 模型选择 submit_refund 工具
  ↓
Agent Service (agent_tools 节点)
  ├─ 订单归属校验（再次校验）
  ├─ interrupt：弹出退款确认卡片
  ↓
用户点击确认
  ↓
Agent Service /api/actions/resume
  ├─ Command(resume={"confirmed": true})
  ↓
Agent Service 调用 gRPC: SubmitRefund
  ├─ user_id = "u1"
  ├─ order_id = "1001"
  ├─ reason = "不想要了"
  ├─ idempotency_key = "conv-123-t8"
  ↓
Business Service
  ├─ 再次校验订单归属
  ├─ 校验订单状态
  ├─ 检查幂等键
  ├─ 创建退款记录
  ├─ 返回 refund_id
  ↓
Agent Service
  ├─ 模型生成确认回复
  ├─ 返回给用户
```

**关键点**：

1. Agent Service 判断"需要确认"
2. Business Service 执行"真正的退款"
3. 业务服务必须再次校验所有条件
4. 使用幂等键防止重复提交

### 6.3 工单创建流程

```text
用户："我要投诉 / 转人工"
  ↓
Agent Service
  ├─ 意图识别：投诉 / 人工
  ├─ 路由到 complaint_reply 或 main_agent
  ├─ 模型选择 create_ticket 工具
  ↓
Agent Service (agent_tools 节点)
  ├─ JSON Schema 校验参数
  ├─ 参数齐全 → interrupt：弹出工单预览
  ├─ 参数缺失 → 回灌错误信息，模型追问用户
  ↓
用户确认工单预览
  ↓
Agent Service /api/actions/resume
  ├─ Command(resume={"confirmed": true})
  ↓
Agent Service 调用 gRPC: CreateTicket
  ├─ user_id = "u1"
  ├─ conversation_id = 123
  ├─ description = "商品有问题"
  ├─ ticket_type = "售后"
  ├─ idempotency_key = "conv-123-t9"
  ↓
Business Service
  ├─ 生成工单号
  ├─ 写入工单表
  ├─ 返回 ticket_no
  ↓
Agent Service
  ├─ 更新会话状态为"已转人工"（写 Agent DB）
  ├─ 返回工单号给用户
```

**注意**：

- 会话状态（`conversations.status`）由 Agent Service 维护
- 工单数据由 Business Service 维护
- 不要在 Business DB 中保存会话数据

---

## 七、安全与权限

### 7.1 用户身份传递

**原则**：`user_id` 必须从可信上下文注入，不能由模型填写。

当前流程：

```text
前端请求
  ├─ user_id: "u1" (从会话或 JWT 中提取)
  ↓
Agent Service
  ├─ 保存在 ConversationState
  ├─ 传递给 Business Service
```

拆分后：

```text
API Gateway
  ├─ 从 JWT 或 Session 提取 user_id
  ├─ 注入到请求头或 gRPC metadata
  ↓
Agent Service
  ├─ 从请求头读取 user_id
  ├─ 保存在 State
  ├─ 调用 Business Service 时传递
  ↓
Business Service
  ├─ 从 gRPC metadata 读取 user_id
  ├─ 校验并执行业务逻辑
```

### 7.2 订单归属校验

**原则**：必须在 Business Service 中执行，不能只在 Agent Service 校验。

当前实现：

```python
# app/tools/business.py
def owns_order(user_id: str, order_id: str) -> bool:
    if not user_id or not order_id:
        return False
    return any(o["order_id"] == order_id for o in list_user_orders(user_id))
```

拆分后：

```java
// Java Business Service
public class OrderService {
    public boolean ownsOrder(String userId, String orderId) {
        if (userId == null || orderId == null) {
            return false;
        }
        Order order = orderRepository.findByOrderId(orderId);
        if (order == null) {
            return false;
        }
        return order.getUserId().equals(userId);
    }
}
```

### 7.3 权限分类

| 工具 | 权限 | 校验位置 |
|---|---|---|
| `query_order` | Read | Business Service |
| `query_logistics` | Read | Business Service |
| `query_faq` | Read | Agent Service |
| `submit_refund` | Write | Business Service |
| `create_ticket` | Write | Business Service |

**Write 操作要求**：

1. Agent Service 必须通过 interrupt 等待用户确认
2. Business Service 必须再次校验权限
3. 使用幂等键防止重复操作
4. 记录审计日志

---

## 八、可观测性

### 8.1 日志规范

#### Agent Service

记录内容：

- 意图识别结果
- 工具调用决策
- 模型 Token 消耗
- 检索召回数量
- 置信度得分
- 上下文窗口大小

日志格式：

```text
INFO:app.graph.nodes:model_ctx conv=123 step=1 summary="早期3轮摘要" window=5条 本轮材料=300字 tokens≈2048
INFO:app.graph.nodes:agent_step conv=123 step=2 input=150 cache_read=1024 total=200
INFO:app.core.observability:tool_run conv=123 tool=query_order source=builtin status=成功 duration_ms=45
```

#### Business Service

记录内容：

- RPC 请求来源
- 订单归属校验结果
- 业务规则判断
- 数据库操作耗时
- 错误码和错误原因

日志格式：

```text
INFO  [OrderService] user=u1 order=1001 action=query result=success duration=12ms
WARN  [OrderService] user=u1 order=9999 action=query result=ORDER_NOT_OWNED
ERROR [RefundService] user=u1 order=1001 action=submit error=ALREADY_REFUNDED
```

### 8.2 链路追踪

使用 `conversation_id` 作为全局追踪 ID：

```text
前端请求 conversation_id=123
  ↓
Agent Service (conversation_id=123)
  ├─ gRPC metadata: trace-id=123
  ↓
Business Service (trace-id=123)
  ├─ 日志中记录 trace-id
```

推荐工具：

- OpenTelemetry
- Jaeger
- Zipkin

### 8.3 监控指标

#### Agent Service

- 对话轮次
- 意图分布
- 工具调用次数
- 模型调用延迟
- 检索召回率
- 置信度分布
- 中断率

#### Business Service

- RPC 请求量
- RPC 延迟（P50/P95/P99）
- 订单查询 QPS
- 退款成功率
- 工单创建量
- 错误码分布

---

## 九、迁移实施计划

### 9.1 阶段划分

#### 阶段 0：准备阶段（1 周）

**目标**：明确服务边界，定义 RPC 契约。

任务：

- [ ] 编写 Protobuf 接口定义
- [ ] 确定数据库拆分方案
- [ ] 设计业务服务 Java 工程结构
- [ ] 搭建 gRPC 脚手架

验收：

- Protobuf 文件可编译
- Java 项目可启动
- gRPC Server 可接受请求

#### 阶段 1：Business Service 开发（2-3 周）

**目标**：实现 Java 业务服务，提供 gRPC 接口。

任务：

- [ ] 实现 OrderService（QueryOrder / ListUserOrders）
- [ ] 实现 LogisticsService（QueryLogistics）
- [ ] 实现 AftersalesService（QueryWarranty / QueryReturnStatus）
- [ ] 实现 RefundService（ValidateRefund / SubmitRefund）
- [ ] 实现 TicketService（CreateTicket）
- [ ] 迁移订单归属校验逻辑
- [ ] 编写单元测试

验收：

- 所有 gRPC 接口可独立测试
- 订单归属校验通过
- 退款幂等性测试通过
- 工单创建测试通过

#### 阶段 2：Agent Service 适配（1-2 周）

**目标**：将 Agent Service 中的业务调用改为 gRPC 调用。

任务：

- [ ] 实现 gRPC Client（Python）
- [ ] 改造 `app/tools/engine.py` 为 RPC 适配层
- [ ] 修改 `app/tools/builtin/orders.py` 为 RPC 调用
- [ ] 修改 `app/tools/builtin/refunds.py` 为 RPC 调用
- [ ] 修改 `app/tools/builtin/tickets.py` 为 RPC 调用
- [ ] 移除 MCP Server 进程（功能已迁移到 Java）
- [ ] 保留工具注册表和执行引擎框架

验收：

- Agent Service 可通过 gRPC 调用 Business Service
- 订单查询流程端到端测试通过
- 退款确认流程端到端测试通过
- 工单创建流程端到端测试通过

#### 阶段 3：数据库拆分（1 周）

**目标**：物理隔离两个服务的数据库。

任务：

- [ ] 创建 `business_db` schema
- [ ] 迁移 `tickets` 表到 Business DB
- [ ] 创建 `orders`、`logistics`、`refunds` 表
- [ ] 配置数据库用户权限
- [ ] 禁止 Agent Service 访问 Business DB

验收：

- Agent Service 只能访问 `agent_db`
- Business Service 只能访问 `business_db`
- 跨服务查询必须通过 RPC
- 数据迁移无丢失

#### 阶段 4：集成测试与上线（1 周）

**目标**：端到端测试，灰度发布。

任务：

- [ ] 运行现有的 pytest 测试套件
- [ ] 运行 `make eval-ch06` 验收脚本
- [ ] 运行 `make eval-ch08` 验收脚本
- [ ] 压力测试
- [ ] 部署到测试环境
- [ ] 灰度发布到生产环境

验收：

- 所有现有测试通过
- 性能指标不劣化
- 用户无感知切换

### 9.2 回滚策略

每个阶段都应支持回滚：

| 阶段 | 回滚方式 |
|---|---|
| 阶段 1 | Business Service 未上线，无需回滚 |
| 阶段 2 | 回退 Agent Service 代码，恢复 MCP Server |
| 阶段 3 | 回退数据库配置，恢复共享数据库 |
| 阶段 4 | 切换流量到旧版本 |

### 9.3 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| gRPC 调用超时 | 用户请求失败 | 设置合理超时，实现熔断降级 |
| 数据迁移丢失 | 业务数据不一致 | 先共享数据库，后物理隔离 |
| 订单归属校验不一致 | 安全漏洞 | Business Service 必须再次校验 |
| 幂等键冲突 | 重复操作 | 使用 `conversation_id + tool_call_id` 作为幂等键 |
| 分布式事务 | 数据不一致 | 避免跨服务事务，使用 Saga 或补偿 |

---

## 十、验收标准

### 10.1 功能验收

| 功能 | 验收方式 |
|---|---|
| 订单查询 | 用户问"订单 1001 的物流"，返回正确物流信息 |
| 订单归属校验 | 用户查询不属于自己的订单，返回"未找到" |
| 退款流程 | 用户申请退款，弹出确认卡片，确认后创建退款单 |
| 工单创建 | 用户投诉，弹出工单预览，确认后创建工单 |
| 知识检索 | 用户问"运费怎么算"，从知识库返回正确答案 |
| 流式输出 | 回答逐 token 流式返回，工具调用实时显示 |

### 10.2 性能验收

| 指标 | 目标 |
|---|---|
| 订单查询 P95 延迟 | < 100ms |
| gRPC 调用 P95 延迟 | < 50ms |
| 对话轮次 P95 延迟 | < 3s |
| 并发用户数 | ≥ 100 |

### 10.3 安全验收

| 项 | 验收方式 |
|---|---|
| 订单归属校验 | 尝试查询不属于自己的订单，必须被拒绝 |
| 退款幂等性 | 重复提交同一退款请求，只创建一次退款单 |
| 工单幂等性 | 重复提交同一工单请求，只创建一次工单 |
| 用户身份伪造 | 尝试修改 `user_id`，必须被拒绝 |

### 10.4 可观测性验收

| 项 | 验收方式 |
|---|---|
| 链路追踪 | 一次对话的所有 RPC 调用都有相同的 trace-id |
| 日志完整性 | 工具调用、错误、耗时都有日志记录 |
| 监控指标 | Prometheus 可抓取 Agent 和 Business 的指标 |

---

## 十一、技术债务与后续优化

### 11.1 已知技术债务

| 项 | 现状 | 优化方向 |
|---|---|---|
| 订单数据 Mock | 当前订单数据是内存生成的 | 接入真实订单系统 |
| 物流数据 Mock | 当前物流数据是随机生成的 | 接入真实物流系统 |
| 用户认证 | 当前 `user_id` 从请求直接传入 | 接入 SSO 或 OAuth2 |
| 分布式事务 | 当前无跨服务事务 | 引入 Saga 或 TCC |
| 配置中心 | 当前配置写在 `.env` | 使用 Nacos / Apollo |

### 11.2 后续优化方向

#### 拆分知识服务

当知识库规模增长、团队边界明确后，可以将知识相关能力独立：

```text
Knowledge Service
  ├─ 知识库录入
  ├─ Chunk 管理
  ├─ Embedding
  ├─ Milvus 检索
  ├─ 知识审核
  └─ 飞轮流水线
```

#### 引入消息队列

对于非实时操作（如知识库向量化、飞轮流水线、评估任务），可以引入消息队列：

```text
Agent Service → Kafka → Knowledge Worker
```

#### API Gateway

引入 API Gateway 统一处理：

- 认证授权
- 限流熔断
- 路由转发
- 日志追踪

---

## 十二、附录

### 12.1 Protobuf 完整定义

见单独文件：`business_service.proto`

### 12.2 Java 工程结构

```text
business-service/
├── src/main/java/com/shangui/userhelp/
│   ├── order/{api,domain,mapper,service}
│   ├── logistics/{api,domain,mapper,service}
│   ├── aftersales/{api,domain,mapper,service}
│   ├── refund/{api,domain,mapper,service}
│   ├── ticket/{api,domain,mapper,service}
│   ├── common/{error,web}
│   └── rpc/
│       ├── OrderGrpcEndpoint.java
│       └── ...
├── src/main/resources/
│   ├── application.yml
│   └── mapper/
├── pom.xml
└── Dockerfile
```

### 12.3 Python Agent Service 改造清单

需要修改的文件：

```text
app/tools/engine.py        # 改造为 gRPC Client 适配层
app/tools/builtin/orders.py   # 改为 RPC 调用
app/tools/builtin/refunds.py  # 改为 RPC 调用
app/tools/builtin/tickets.py  # 改为 RPC 调用
app/tools/mcp_client.py        # 移除或保留为外部工具接入
app/config.py                  # 增加 Business Service 地址配置
```

需要新增的文件：

```text
app/grpc/
  ├── __init__.py
  ├── client.py              # gRPC Client 封装
  ├── business_pb2.py        # Protobuf 生成的消息类
  └── business_pb2_grpc.py   # Protobuf 生成的服务类
```

需要删除的文件：

```text
mcp_servers/logistics_server.py    # 功能迁移到 Java
mcp_servers/aftersales_server.py   # 功能迁移到 Java
app/tools/business.py               # 功能迁移到 Java
```

---

## 总结

本规格书定义了 MewHelp 系统从单体架构拆分为"Python Agent Service + Java Business Service"的完整方案，包括：

1. 服务职责划分
2. RPC 接口契约
3. 数据库拆分方案
4. 关键流程设计
5. 安全与权限控制
6. 可观测性要求
7. 迁移实施计划
8. 验收标准

按照本规格书实施，可以实现：

- Agent 编排与业务逻辑解耦
- Python 和 Java 各自发挥技术优势
- 团队按领域独立开发和部署
- 数据边界清晰，安全可控
- 可独立扩展和演化

下一步请其他 agent 或开发人员按照本规格书进行实施。
