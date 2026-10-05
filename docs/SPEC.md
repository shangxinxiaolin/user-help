# 灵犀客服微服务架构规格书

> 本文档描述服务边界与目标架构。Java 细节以 `business-service/docs/JAVA_BUSINESS_SERVICE_SPEC.md` 和
> `business-service/src/main/proto/business_service.proto` 为准；Python 细节以
> `agent-service/docs/PYTHON_AGENT_SERVICE_SPEC.md` 为准。

## 文档目的

本文档定义灵犀客服的目标服务边界：

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
agent-service/（能力规划示意，部分模块尚未实现）
├── app/
│   ├── api/          # HTTP 接口层
│   ├── graph/        # LangGraph 工作流
│   ├── core/         # 核心能力（LLM、意图、检索、上下文、飞轮）
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

#### 1.5.5 上下文管理（三层分层：原文 + 截短 + 摘要）

**位置**：`app/core/memory.py`、`app/core/summarizer.py`、`app/graph/nodes.py:_agent_messages`

**问题**：对话历史无限累积会撑爆上下文窗口；纯滑窗只认位置不认内容，扛不住用户回翻旧话题。

**解决方案（会话内三层，越近越完整、越远压得越狠）**：

```text
历史消息（按自增 id 排序）
  ├─ 层1 最近 N 轮：原文一字不压（context_window_turns=8）
  │     指代消解、意图判断靠精确措辞，近处必须保真
  ├─ 层2 中间：规则截短，不调模型
  │     用户原话不动；客服答复只留开头几十字；大工具结果换一行标识
  └─ 层3 远处：后台异步摘要（conversations.summary + summary_upto_msg_id）
        一段段攒、压完定死不回头重写（防多次有损压缩磨掉订单号）

发送给模型时组合
  ├─ SystemMessage（人设 + 工具 schema，逐字不变）
  ├─ 层2 截短历史
  ├─ 层1 最近原文
  ├─ 用户当前这句
  └─ 本轮材料（层3 摘要 + 检索证据 + 订单数据，挂用户句后，不进 system）
```

**选择历史三种方法（本项目只做滑窗，另两种按需加）**：

| 方法 | 维度 | 补的窟窿 |
|---|---|---|
| 滑动窗口 | 位置 | 固定带最近几轮，保时序连贯（打底） |
| 语义检索 | 内容 | 捞回远处语义相关旧轮，应对用户回翻 |
| 主题重要度 | 关键事实 | 单独留底（如"要开发票"），不随窗口裁掉 |

**摘要触发（看用量，不数条数）**：

```text
每轮对话结束
  ↓
检查层2 已占 token 是否超预算
  ↓
（工具结果不落消息表，数条数看不见；一轮长短不定，只能按用量）
  ↓
后台异步生成摘要（不阻塞当前回复）
  ↓
更新 conversations.summary + summary_upto_msg_id
```

**各层额度（从模型窗口倒推，不写死常量）**：

```text
窗口 = system/工具定义 + 检索证据 + 注入摘要 + 输出预留 + 历史
历史预算 = min( N × (X+Y), 窗口 - 固定开销 )   // X=单轮输入上限, Y=单轮输出上限
层1 七成、层2 三成；层1 超预算降级到层2，层2 超预算压成摘要

中文 token 口径：默认 4 字符=1 token 是英文口径，中文 1 字≈1 token；
裁剪闸门与预算用同一校准口径，全链路只走一个换算入口（统一当除数）。
```

**前缀缓存优化**：

```text
SystemMessage + 工具 schema 保持逐字不变
  ↓
摘要/证据每轮可变，挂在用户句后，不塞进 system
  ↓
上游缓存命中（cache_read token）
```

**State 边界**：

```text
State.messages 只进不出（事实源 + checkpoint，add_messages 自动追加）
分层动的是每轮现拼的精简版，靠两个 id 切三段，只挪数字不搬数据
上下文只管当前这一通会话，不跨会话、不攒用户画像
```

**拆分归属**：Agent Service

---

#### 1.5.6 主题分类器（微调，可选模块）

**位置**：`scripts/ch10/`、`app/core/taxonomy.py`

**目的**：旁路批量归类低置信度问题，统计各主题分布，排出补知识优先级。

**何时微调（决策依据）**：

```text
第一原则：能用提示词就别微调（微调动参数，前期投入大、见效慢）
触发微调的三道坎：
  1. few-shot 举不完（每类说法无穷无尽）
  2. 方言/口语/错别字逐条打标易错、答案飘忽
  3. 万级问题逐条调大模型又贵又慢
算账：量大（万级）+ 类目稳（一年不换）才回本；类目常变则投入打水漂
微调救不了数据没治理干净（含糊/类目重叠/自相矛盾）→ 回头修数据和类目定义
```

**任务与选型**：

```text
任务：多标签文本分类，字面提到几个主题就标几个
  意图识别 = 会话维度（对话状态追踪，读整段历史）→ 走大模型，不微调
  主题归类 = 单句维度（上游指代消解 + 标准化已去上下文）→ 适合小模型微调
选型：分类用编码器模型（整句压向量、每类独立出分），不用生成式大模型
  RoBERTa-wwm-ext（哈工大讯飞，约 1 亿参数）全参微调，消费级显卡可跑
  PEFT / LoRA / QLoRA 留到几十亿参数模型再启用
```

**数据四步（胜负手在数据，不在模型）**：

```text
1. 清洗：手机号/订单号脱敏，错别字、格式、标注手误一并处理
2. 归并术语表：同类说法收拢到同一标准类目，全系统只认一份
   每类配边界说明 + 说法示例（如"退货/退款/退钱/想退了" → 退换货）
3. 划分数据集：训练/验证/测试 8:1:1，按类目分层抽样，每类按比例出现在三份
4. 数据增强：同义替换、改口气，只扩训练集；验证/测试保持原样（防考前漏题）
标注规范：字面提到几个标几个，不把类目关联的活揽到标注上
```

**标注方式**：

```text
大模型照术语表预标 → 人工抽样把关
标签噪声（同说法标出多种组合）→ 回头按"字面几个标几个"重新对齐
欠拟合/过拟合 → 效果不行先搞数据；配正则化 + 早停
```

**流程**：

```text
低置信度问题池
  ↓
批量调用分类器推理服务（:8110 ONNX）
  ↓
写入 topic_classifications
  ↓
前端展示主题分布（/topics 页面）→ 排补知识优先级
```

**训练流程**：

```bash
make ch10-corpus     # 生成语料（含清洗脱敏）
make ch10-dataset    # 分层抽样划分训练/验证/测试集
make ch10-train      # RoBERTa-wwm-ext 全参微调
make ch10-export     # 导出 ONNX
make ch10-eval       # 测试集评估
```

**验证**：

```text
指标：精确率（打上的标签里多少是对的）/ 召回率（该打的漏了多少）/ F1 + 混淆矩阵
容错红线：按类目定义误判容忍度（有些归错无伤大雅，有些后果严重）
评测集扎在自家电商场景造，不用 MMLU/C-Eval 公开榜单替代
```

**推理服务**：

```bash
make classifier-up   # 启动 :8110
make classify-pool   # 批量归类
```

**延伸**：

```text
Embedding 也能微调（校准"满减""花呗分期"等黑话召回），但是最后手段：
先做切分、混合检索、重排，都到位还差一口气才动 Embedding 微调
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

**选型理由与触发场景**（准确率/召回率/延迟等数值待开发后用自家评估集实测，此处只给定性理由）：

| 选型 | 为什么选 | 什么场景才用得上 / 何时不用 |
|---|---|---|
| LangChain | 封装 ChatOpenAI/PromptTemplate/结构化输出 | 接 LLM + Prompt 工程地基 |
| LangGraph | 要分流、汇合、循环、状态贯穿 | 链式结构拼不出来时 |
| 嵌入模型 BGE-M3 | 私有化部署、可领域微调、中英双强 | 生产自部署；课程演示可用云端 |
| Milvus | 一库扛 dense + BM25 + RRF | demo 嫌重可先用 ChromaDB 起步 |
| bge-reranker | Cross-Encoder 排得准 | 召回够全但前排不够相关时才需要 |
| 意图识别 LLM+prompt | 多轮 = 对话状态追踪 | 单句分类才用规则/微调小模型 |
| LangGraph State | 上下文随图流转 | 会话上下文唯一事实源 |
| @tool + MCP | 内置工具 + 外部系统即插即用 | 核心业务动态工具走 MCP |
| Langfuse | 开源自部署、零侵入还原调用树 | 不介意上云换 LangSmith |
| RoBERTa-wwm-ext | 编码器适合分类、全参够用 | 词表稳 + 口语丰富 + 成本卡死才微调 |

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
| 上下文管理 | 三层分层（原文/截短/摘要）、前缀缓存 |
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

- `tickets` 的最终归属为 Java Business Service；Java Mock 阶段不写 Agent DB，避免跨服务直接写库。
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

当前本地开发状态（不是可信身份验证）：

```text
前端请求
  ├─ user_id: "u1" (目前由请求提供，仅供本地开发)
  ↓
Agent Service
  ├─ 保存在 ConversationState
  ├─ 传递给 Business Service
```

对外部署目标：

```text
API Gateway / 反向代理
  ├─ TLS、IP 限流与请求体大小限制
  ├─ 仅转发允许对外开放的路由
  ↓
Agent Service
  ├─ 校验 JWT/Session 并提取 user_id，不信任请求 Body/Header 自报的身份
  ├─ 校验 conversation_id 属于当前用户
  ├─ 用户请求频率、并发及模型 Token 配额检查（调用模型之前）
  ├─ 保存在 State
  ├─ 调用 Business Service 时传递身份和 trace-id
  ↓
Business Service
  ├─ 校验调用方是 Agent Service
  ├─ 使用可信身份执行业务归属、退款规则与幂等校验
```

现有 Protobuf 的 `RequestContext.user_id` 是开发阶段的传递格式，不等于认证；Java 当前 gRPC/HTTP 调试接口也未实现服务身份认证。未来改用可信 metadata 或透传并验证用户令牌时，先制定兼容的接口迁移方案，不把未实现的 metadata 校验描述为现状。

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

### 7.4 公网接入与模型费用保护

当前只在本地调试，`/api/chat` 与 `/api/agent` 尚未接入认证或配额；不能把当前 FastAPI 或 Java 调试端口直接暴露公网。部署前必须先完成下列边界：

| 边界 | 责任 | 拒绝时机 |
|---|---|---|
| 网关/反向代理 | TLS、IP 限流、Body 上限；只放行公开路径 | 转发到 Agent 前 |
| Python Agent | JWT/Session 认证、会话归属、用户限流/并发/日 Token 配额、输入和输出预算、LLM 超时、最大 ReAct 步数 | Graph/LLM 执行前及运行中 |
| Java Business | 限制公网可达性、服务间认证、订单归属及业务规则、退款/工单幂等 | 业务读写前 |

- `/api/chat`：经认证和配额检查后才对前端开放；限制单用户活跃 SSE 连接和全局模型并发。客户端断开时尽力取消正在进行的 Graph/LLM 任务，记录取消与实际用量，不能把取消视为已退回上游 Token。
- `/api/agent`：包含完整 Agent 信息，目标为内部/管理员接口，不经公网普通用户路由。
- `/api/actions/resume`：必须复核认证用户与会话归属；用户确认不能替代 Java 的最终业务校验。
- 配额采用用户级持久/共享计数及原子占额（多实例时可用 Redis）；发起调用前检查，拿到实际 usage 后结算。并发槽位必须在正常完成、失败与取消时释放。限流时返回 429，且不启动模型调用。
- SSE 头部发送后不能再更改 HTTP 状态码：流中出错发送 `error` 事件并终止；在发送头部前完成认证/配额检查，可返回 401/403/413/422/429 等状态码。
- 具体阈值应在配置和压测后确定，不能以示例数字冒充已验证的容量承诺；网关、认证和配额均列为公网发布前置条件，而非现有功能。

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

### 9.0 阶段闸门规则

整体开发采用按架构分阶段实施的方式。每个阶段完成后必须完成测试、汇报变更和遗留问题，并等待用户明确确认后，才能进入下一阶段。

```text
阶段目标
  ↓
实施
  ↓
验证
  ↓
向用户汇报
  ↓
用户确认
  ↓
下一阶段
```

未获得确认时，不得跨阶段实现、删除回滚路径或修改后续模块。

### 9.1 阶段划分

#### 阶段 0：准备阶段（1 周）

**目标**：明确服务边界，定义 RPC 契约。

任务：

- [ ] 编写 Protobuf 接口定义
- [ ] 确定数据库拆分方案
- [ ] 设计业务服务 Java 工程结构
- [ ] 搭建 gRPC 脚手架

阶段完成后暂停，等待用户确认 Proto 契约、目录结构和服务边界。

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

Java Business Service 内部继续拆成订单、物流、售后、退款、工单多个子阶段；每个业务模块完成后分别验收，不一次性跨过所有模块。

验收：

- 所有 gRPC 接口可独立测试
- 订单归属校验通过
- 退款幂等性测试通过
- 工单创建测试通过

#### 阶段 2：按原能力重新实现 Agent Service（分阶段）

**目标**：在 `agent-service` 中完善对话编排、检索与工具执行；业务工具通过 gRPC 调用 Java Business Service。

任务：

- [ ] 创建新的 Python Agent Service 骨架
- [ ] 重新实现基础 FastAPI 和 LangGraph 对话流程
- [ ] 实现 Python gRPC Client
- [ ] 重新实现订单 Tool，并调用 Java RPC
- [ ] 重新实现物流和售后只读 Tool
- [ ] 重新实现退款确认流程
- [ ] 重新实现工单确认流程
- [ ] 如接入 MCP，将其限定为外部动态工具，不与 Java 核心业务能力重复

Python 重实现顺序固定为：项目骨架 → 基础 Agent → gRPC 基础设施 → 订单 → 物流/售后只读工具 → 退款 → 工单。每一项完成后都必须与用户确认再进入下一项。

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

只有在 Mock 业务链路和 Python/Java 联调验收后，才讨论真实数据库；进入本阶段需要用户单独确认。

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

当前学习项目只要求完成本地集成测试；部署、灰度和生产发布属于后续阶段，不能默认执行。

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
| 模型请求频率/配额 | 超限时在调用模型前返回 429；后端模型调用计数不增加 |
| 会话归属和恢复 | 使用他人的 `conversation_id` 或 resume 请求必须被拒绝 |
| 公网路径 | `/api/agent`、管理接口与 Java gRPC/调试接口不得向普通公网用户开放 |
| SSE 断线 | 断线后取消本地生成任务、释放并发占位；记录可获得的上游用量，无法获得时标记待对账 |

本节新增的公网防护均为**部署前目标**，当前本地项目尚未实现，不能将验收表描述为已通过。

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

## 十二、学习 Chiron 的工程设计与实施要求

新增日期：2026-10-05。状态：学习与分阶段实施要求；不代表以下能力已经完成。

### 12.1 学习目标与范围

继续以灵犀客服为主项目，以 `D:\hello\Chiron-Agent` 为工程参考。目标是做成一条可演示、可解释、可测试的「订单查询 → 政策解释 → 用户确认 → 退款执行 → 结果查询」闭环，而不是复制 Chiron 的全部框架。

本节补充现有分阶段计划。Java 前置入口、身份模型、数据库和公开接口变更仍须先确认；本节不自动批准这些变更，不改变当前 Python HTTP 入口与 Java gRPC 业务服务的调用关系。每个阶段完成后测试、讲解并等待确认，再进入下一阶段。

当前实现基线（静态代码阅读，未运行验证）：

- Java 已有订单、物流、售后、退款、工单服务及 gRPC Endpoint，业务数据为 Mock；退款与工单幂等记录在内存中。
- Python 当前 Graph 为 `START → chat → log → END`；会话/消息 ORM、仓储和 SQLite checkpointer 封装已经存在，完整工具循环、RAG 与业务 gRPC 客户端尚未贯通。
- `agent-service/app/main.py` 已设置 `app.state.graph`，但路由注册与聊天处理引用未定义的 `graph`，应先修复入口并验证持久化 Graph 的实际使用。
- 规格中的置信度闸、知识飞轮和对话挖知识属于后续能力，不能作为当前已实现成果介绍。

### 12.2 从 Chiron 学什么

以下参考路径相对于 Chiron 仓库根。学习完成后，应能够解释设计解决的问题，并用灵犀客服的测试验证对应行为。

| 灵犀客服要解决的问题 | 学习内容 | Chiron 参考入口 | 灵犀客服落点 |
|---|---|---|---|
| 客户端伪造用户、会话或资源引用 | 从可信身份重建调用上下文；资源归属校验 | `backend/bff/src/main/java/com/hewei/hzyjy/xunzhi/modules/decision/application/evaluation/DecisionEvaluationInvocationAssembler.java`；`backend/interview-agent/app/common/http/account_scope.py` | API 身份上下文、会话仓储、gRPC RequestContext、Java 业务归属校验 |
| 模型选择了不允许执行的动作 | 工具目录与执行前准入；模型提出动作，代码决定能否执行 | `backend/interview-agent/app/runtime/agent/loop.py`；`app/runtime/tools/`；`app/composition/capability_catalog.py` | 现有 Graph、工具注册与执行适配层；不另造第二套执行循环 |
| 重试造成重复业务操作 | 区分请求、用户消息和业务操作身份；幂等键绑定输入 | `backend/interview-agent/app/modules/evaluations/application/lifecycle/commands.py` | 退款/工单服务、业务操作幂等记录、Python 工具调用上下文 |
| 断线、超时与业务状态混淆 | 订阅生命周期与任务生命周期分离；恢复时读取权威状态 | `backend/interview-agent/app/modules/evaluations/application/agent/program.py`、`task_stream.py`；`frontend/src/services/decision/agent/invokeStream.ts` | checkpoint、操作结果查询、后续 SSE 恢复设计 |
| Java 前置后流式输出被缓冲 | 流式转发、及时 flush、禁用代理缓冲、释放连接资源 | `backend/bff/src/main/java/com/hewei/hzyjy/xunzhi/modules/decision/api/DecisionSseEndpointSupport.java`；`infrastructure/pyagent/PyAgentWebTransport.java`；`frontend/docker/chiron-app.inc` | 后续 Java HTTP/SSE 入口及反向代理配置，实施前确认 |
| 回答没有依据、无法证明效果 | 来源与结论分离；固定案例与 outcome eval | `docs/architecture/ARCHITECTURE-CONTRACT.md` 的 grounding 边界；`backend/interview-agent/evals/docs/how-we-measure.md` | 政策检索、置信度闸、客服案例集与评测报告 |
| 两端维护不同版本的同一状态 | single-writer、契约真相源与边界测试 | `skills/repo/architecture/references/data-ownership.md`；`docs/architecture/ARCHITECTURE-CONTRACT.md` | Java 持有交易业务，Python 持有对话与 Graph 状态 |

### 12.3 状态所有权与执行边界

- Java 是订单、物流、售后、退款与工单的权威方；普通 API 和 Agent 工具调用必须复用同一业务服务。
- Python 是对话、消息、上下文、待确认流程和 Graph checkpoint 的权威方。Java 前置后也不再复制一套消息历史或 Graph 状态。
- Python 记录工具调用过程，Java 记录业务操作结果；两者通过操作标识关联，不能各自维护一份退款状态。
- 模型不决定用户身份、资源权限或最终退款资格。Java 在写操作处重新校验归属与业务条件，不能仅依赖此前的查询或模型判断。
- RAG 用于解释政策和提供引用，Java 业务规则决定是否执行。检索不到或证据不足时应澄清或转人工，不编造政策。
- 用户确认绑定具体订单、操作参数与操作标识。参数改变后必须重新确认；自由文本中的“确认”不能授权任意后续写操作。
- 工具仅接收业务参数；可信用户身份由服务端上下文注入，不能由模型填写。暂用身份头联调时须明确其为开发机制。

### 12.4 重试、恢复与幂等要求

明确区分以下概念，不要求沿用 Chiron 的字段名称，但实现前须确定契约：

| 标识 / 行为 | 含义 |
|---|---|
| 请求标识 | 一次调用尝试及日志关联，不等于一笔业务操作 |
| 用户消息标识 | 防止同一条用户消息重复推进流程 |
| 业务操作幂等键 | 同一笔退款或工单在重试中保持不变，按用户和操作类型隔离，并绑定输入指纹 |
| checkpoint | 保存编排状态，不代替 Java 业务数据库与操作结果 |
| 恢复订阅 | 补收已有事件，不重新发送退款指令 |
| 取消等待 | 停止客户端等待，不表示已提交的退款被撤销 |

持久化写操作的验收要求：

1. 相同幂等键、相同参数返回原操作结果；相同键、不同参数明确报冲突。
2. 并发重复提交也只产生一笔操作，依靠数据库唯一约束与事务保证，不仅做“先查询再插入”。
3. 业务结果和幂等记录的提交保持一致；进程重启后仍能查询原结果。
4. gRPC 超时表示结果未知，不能直接判断执行失败并生成新幂等键。应使用原键查询或重试，取得已有结果。
5. 用户确认前不执行写操作；重复确认、模型重复工具调用、客户端重试不能产生第二笔退款。
6. 不承诺网络层“恰好一次”；通过可重试调用与幂等业务执行保证重复请求不产生重复业务效果。

若后续引入长任务与事件回放，必须先定义任务 owner、事件序号、游标和取消语义，再选择 worker/outbox；当前阶段不为普通查订单先引入整套持久化任务平台。

### 12.5 Java 前置入口的后续评估

候选生产架构为：`客户端 → Java 产品入口 → Python Agent → gRPC → Java 业务服务`。Java 产品入口和业务服务初期可在同一 Spring Boot 应用中分层实现。

实施前确认以下事项：

- 登录身份由 Java 验证，并向 Python 传递可信上下文；Python 内部接口有服务鉴权，不能只信任任意客户端提交的用户头。
- 普通订单/退款查询直接走 Java；需要自然语言理解的请求进入 Python。
- SSE 保留事件名、事件 ID 与数据，及时 flush，并关闭反向代理缓冲。
- 分别定义连接、首字节、空闲和绝对总时长超时；以实际执行语义和测试为准，不能仅凭配置字段名称判断。
- 浏览器断线后释放订阅和并发资源；是否停止 Python 执行按具体操作定义，不能把断线默认当成业务取消。
- 流开始前的 HTTP 错误、流中的业务失败、传输中断分别处理。不得把连接失败直接等同于退款失败；必要时查询权威操作结果。
- 使用有限并发、连接池和限流控制资源。采用 `Flux` 不等于整个 MVC 输出链完全非阻塞，仍需验证线程池与慢客户端行为。

Chiron 提供参考实现而非可直接复制的标准：其 Transport 中 `Flux.timeout(Duration)` 主要限制事件间等待，并非绝对总时长；部分代理异常会转换成 `agent.task.failed`。灵犀客服应按自身业务定义超时和恢复语义，不继承这些细节作为默认结论。

### 12.6 分阶段实施与验收

| 阶段 | 工作范围 | 最低验收标准 |
|---|---|---|
| A：基础接线 | 修复 FastAPI 入口，接入会话仓储和 checkpoint | 应用可启动；会话只能由所属用户读取/续聊；消息入库；关闭并重建应用后可读到同一会话 checkpoint |
| B：只读业务链 | Python 工具 → gRPC → Java 查询订单 | 自然语言查询实际调用 Java；缺订单号时澄清；无权访问时拒绝；超时有明确结果；Fake gRPC 测试与至少一次跨服务联调 |
| C：可靠退款 | 明确确认状态；Java 持久化退款与幂等 | 未确认不写；重复/并发确认只生成一笔；不同参数复用键报冲突；重启后仍可查结果；提交后响应丢失可用原键取得原结果 |
| D：政策依据与评测 | 小范围政策 RAG、引用与低置信度处理 | 回答可追溯政策来源；无依据时降级；业务资格仍由 Java 判断；固定案例输出真实评测结果 |
| E：统一产品入口 | 经确认后增加 Java 鉴权与 Agent HTTP/SSE 转发 | 身份不可由请求正文覆盖；事件及时到达；断线释放资源；传输错误与业务结果不混淆；不复制 Python 权威状态 |

阶段 C 涉及业务数据库与接口语义，阶段 E 涉及入口和身份架构，均须先确认设计再实施。优先完成 A–D 的核心闭环，不并行铺开全部业务和基础设施。

### 12.7 固定案例与项目展示要求

首批案例至少覆盖：正常查询、缺失订单号、跨用户订单访问、不可退款、未确认提交、正常确认、重复确认、并发重复提交、gRPC 超时、提交成功但响应丢失、服务重启、政策检索无命中。

- 确定性测试覆盖归属、状态转移、幂等和故障恢复；使用 Fake 模型与 Fake gRPC 验证可重复行为。
- Agent outcome eval 记录工具选择正确率、参数正确率、流程完成率、引用有效性及未确认写操作次数；明确分母、模型配置和失败案例。
- 未确认写操作、越权业务操作、重复请求产生重复退款均应为 0；这是验收要求，不是当前实测成绩。
- 可选真模型测试单独记录；不将每次都会波动的真模型调用作为基础单测门禁。
- 项目介绍区分已实现、已验证、规划能力；学习 Chiron 时说明参考来源，并能展示自身实现、故障复现和测试证据。

当前不作为前置目标：Graphiti/Neo4j 长期记忆、完整共享 Agent 内核、ARQ/outbox 全套平台、第二套执行循环、仅为目录对称新增模块。以后只有在具体需求与失败场景证明必要时再评估。

---

## 十三、附录

### 13.1 Protobuf 完整定义

见单独文件：`business_service.proto`

### 13.2 Java 工程结构

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

### 13.3 Python Agent Service 改造清单

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

### 13.4 踩坑复盘清单

各章教训收拢，每条回指对应章节：

| # | 坑 | 解法 | 回指 |
|---|---|---|---|
| 1 | 关键词查表必漏召回（SQL LIKE 字面对不上） | RAG 换语义检索 | 第 2→3 章 |
| 2 | 向量单路漏 SKU/型号/优惠券代码 | BM25 + RRF + Rerank | 第 3→4 章 |
| 3 | 切分切歪救不回（条款切两半） | 结构感知切分 + 关键条款标记 | 第 3 章 |
| 4 | 扩召回在入库侧拆成多份占满 Top-K | 检索侧 Query 扩写，库中只存一份 | 第 4 章 |
| 5 | Agent 守不住硬约束（跳过检索/该拒答硬答） | Workflow 写死强制检索/取证/转人工 | 第 5 章 |
| 6 | 意图边界定义不清准确率上不去 | prompt 划清每类边界 | 第 6 章 |
| 7 | 光靠滑窗漏早期上下文 | 三层分层（原文/截短/摘要） | 第 1→7 章 |
| 8 | 数据质量决定微调成败（标签噪声） | 先搞数据、修标注 | 第 10 章 |

规律：越出在数据和流程上的坑越致命，模型再强也补不回切分的一刀、标乱的标签，以及幻觉时的流程。

### 13.5 模块设计文档索引

各模块的设计与选型理由见 `agent-service/docs/design/`：

| # | 文档 | 内容 |
|---|---|---|
| 01 | `01-llm-prompt.md` | LLM 接入与 Prompt 工程 |
| 02 | `02-function-call.md` | Function Call 工具调用 |
| 03 | `03-rag.md` | RAG 混合检索与重排 |
| 04 | `04-workflow-agent.md` | Workflow + Agent 混合架构 |
| 05 | `05-intent-dialogue.md` | 意图识别与对话管理 |
| 06 | `06-context-management.md` | 会话上下文分层管理 |
| 07 | `07-tool-system.md` | 工具系统与 MCP |
| 08 | `08-observability-flywheel.md` | 可观测性与数据飞轮 |
| 09 | `09-model-finetuning.md` | 模型微调 |
| 10 | `10-full-pipeline-review.md` | 全链路串联与复盘 |

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
