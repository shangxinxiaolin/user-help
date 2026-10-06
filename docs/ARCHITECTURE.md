# 灵犀客服架构图

本文集中维护目标架构、当前接线与请求流程。目标图中的实线表示设计调用方向，不代表已实现；当前拓扑中的虚线表示待实现或待联调路径。代码接线存在也不等于已经验收。详细契约见 [总体规格](SPEC.md)。根 README 展示系统概览，服务 README 展示各自局部视图。

<a id="target-architecture"></a>

## 1. 目标架构（E 阶段，尚未实现）

Gateway/BFF 与业务模块同处一个 Spring Boot 项目和进程；Python 是内部 Agent 服务，只回调 Business RPC，不直接访问 Business DB。

```mermaid
flowchart LR
    Client["客户端<br/>Web / App"]

    subgraph Java["Spring Boot（同一进程）"]
        direction TB
        Entry["entry Gateway/BFF<br/>认证鉴权 · 限流 · 产品路由 · SSE 转发"]
        BizSvc["业务 Service<br/>order · logistics · aftersales · refund · ticket"]
        BizRpc["Business RPC<br/>gRPC Server :9090"]
        Entry -->|普通请求| BizSvc
        BizRpc --> BizSvc
    end

    subgraph Python["Python Agent Service（内部）"]
        direction TB
        AgentApi["FastAPI<br/>HTTP / SSE"]
        Graph["LangGraph 工作流"]
        Tools["LangChain Tools + MCP"]
        GrpcClient["gRPC Client"]
        AgentApi --> Graph --> Tools --> GrpcClient
    end

    BizDB[("Business DB<br/>MyBatis")]
    AgentDB[("Agent DB<br/>MySQL")]
    Ckpt[("Checkpoint")]
    Milvus[("Milvus<br/>向量 + BM25")]
    LLM["LLM<br/>OpenAI 兼容接口"]

    Client -->|HTTPS| Entry
    Entry -->|Agent 请求<br/>内部 HTTP/SSE| AgentApi
    BizSvc --> BizDB
    GrpcClient -->|gRPC / Protobuf| BizRpc
    Graph --> AgentDB
    Graph --> Ckpt
    Graph --> Milvus
    Graph --> LLM
```

<a id="current-topology"></a>

## 2. 当前实现（开发阶段拓扑）

统一入口尚未实现，开发时直接请求 Python JSON 接口；Java HTTP 仅用于业务调试；Python 与 Java 的 gRPC 尚未联调。`/api/chat` 已开始仓储注入，`/api/agent` 仍未注入；Fake 模型分支跳过仓储初始化，当前持久化链路未完成验收。

```mermaid
flowchart TB
    Dev["开发者 / 调试客户端"]

    subgraph Agent["agent-service（Python 3.12 · FastAPI）"]
        direction TB
        Chat["POST /api/chat<br/>（注入 ConversationRepository）"]
        AgentEp["POST /api/agent"]
        Health["GET /health"]
        Runtime["graph/runtime.run_turn()"]
        subgraph LG["LangGraph"]
            direction LR
            S((START)) --> ChatNode["chat"] --> LogNode["log"] --> E((END))
        end
        Repo["ConversationRepository<br/>SQLAlchemy Async"]
        ToolsTodo["业务工具 / gRPC Client<br/>（未实现）"]
        Chat --> Runtime
        AgentEp --> Runtime
        Runtime --> LG
        Runtime --> Repo
        LogNode --> Repo
    end

    subgraph Business["business-service（Java 21 · Spring Boot）"]
        direction TB
        Http["BusinessController<br/>HTTP :8080 /api/business/**"]
        Grpc["gRPC Endpoints :9090<br/>Order · Logistics · Aftersales · Refund · Ticket"]
        Svc["Service 接口 + impl<br/>归属校验 · 退款/工单幂等（内存）"]
        Mapper["Mock Mapper"]
        Http --> Svc
        Grpc --> Svc
        Svc --> Mapper
    end

    MySQL[("Agent MySQL<br/>conversations · messages<br/>docker-compose :3307")]
    Sqlite[("SQLite checkpoint<br/>data/checkpoints.sqlite")]
    LLM["LLM<br/>OpenAI 兼容接口"]
    Proto[["business_service.proto<br/>Java / Python 共用契约"]]

    Dev -->|HTTP JSON| Chat
    Dev -->|HTTP JSON| AgentEp
    Dev -->|HTTP 调试| Http
    Dev -->|grpcurl| Grpc
    ChatNode --> LLM
    Repo --> MySQL
    LG -->|正常 lifespan 的 checkpointer| Sqlite
    ToolsTodo -.->|gRPC（未联调）| Grpc
    Proto -.- Grpc
    Proto -.- ToolsTodo

    classDef todo fill:#f4f4f4,stroke:#999,stroke-dasharray:5 5,color:#666
    class ToolsTodo todo
```

<a id="chat-sequence"></a>

## 3. 当前对话请求时序（`/api/chat`）

以下描述正常 lifespan、仓储和表可用时的成功与拒绝路径；现有测试尚待生命周期适配，不宣称运行验收通过。MySQL 写库与 SQLite checkpoint 不属于同一事务，checkpoint 在执行中保存快照，不只在最终回复后写一次。

```mermaid
sequenceDiagram
    autonumber
    participant C as 客户端
    participant API as FastAPI /api/chat
    participant RT as runtime.run_turn
    participant Repo as ConversationRepository
    participant G as LangGraph（chat → log）
    participant LLM as LLM
    participant CP as SQLite checkpoint

    C->>API: message, user_id, conversation_id?
    API->>RT: run_turn(...)
    alt conversation_id 为空
        RT->>Repo: create_conversation(user_id)
    else 已有会话
        RT->>Repo: get_conversation_for_user(id, user_id)
        Repo-->>RT: 会话对象或 None
    end
    alt 不存在或不属于该用户
        RT-->>API: ConversationNotFound
        API-->>C: HTTP 404（不执行 Graph）
    else 允许访问
    RT->>Repo: append_message(role=user)
    RT->>G: ainvoke(state, thread_id=conversation_id)
    Note over G,CP: 执行期间按 checkpoint 机制保存 Graph 快照
    G->>LLM: chat 节点调用模型
    LLM-->>G: AI 回复
    G->>Repo: log 节点落库 assistant 消息
    G->>CP: 保存执行快照
    G-->>RT: ConversationState
    RT-->>API: state
    API-->>C: conversation_id, answer
    end
```

<a id="agent-workflow"></a>

## 4. 目标 LangGraph 工作流（规划）

当前仅实现 `chat → log` 两个节点；下图为 [SPEC 1.3](SPEC.md#13-核心请求链路) 规划的完整链路。

```mermaid
flowchart TB
    Start((START)) --> Resolve["resolve_reference<br/>指代消解"]
    Resolve --> Intent["classify_intent<br/>意图识别"]
    Intent --> Route{"route_by_intent"}

    Route -->|knowledge| Retrieve["retrieve_knowledge<br/>向量 + BM25 + 重排"]
    Retrieve --> Gate{"confidence_check<br/>置信度闸"}
    Gate -->|证据足够| Main
    Gate -->|证据不足| Fallback["fallback_reply"] --> Log

    Route -->|refund_flow| Fetch["fetch_order"] --> Policy["retrieve_policy"] --> Main
    Route -->|business| Main["main_agent<br/>ReAct 工具循环"]
    Route -->|escalate| Complaint["complaint_reply"]
    Route -->|fallback_script| Script["script_reply"]

    Main <--> AgentTools["agent_tools<br/>内置工具 / MCP / gRPC"]
    Main --> Log["log"]
    Complaint --> Log
    Script --> Log
    Log --> End((END))
```

<a id="business-layers"></a>

## 5. Business Service 分层

```mermaid
flowchart LR
    subgraph Entry["接入层"]
        HTTP["business/api<br/>BusinessController"]
        RPC["rpc<br/>*GrpcEndpoint"]
    end
    subgraph Domain["业务模块"]
        direction TB
        Order["order"]
        Logistics["logistics"]
        Aftersales["aftersales"]
        Refund["refund"]
        Ticket["ticket"]
    end
    subgraph Layers["每个模块内部"]
        direction TB
        Service["service 接口"] --> Impl["service/impl"] --> MapperI["mapper 接口"] --> Mock["Mock*Mapper<br/>（后续 MyBatis）"]
        DomainObj["domain"]
    end
    Common["common<br/>BusinessException · ErrorCode · GlobalExceptionHandler"]

    HTTP --> Domain
    RPC --> Domain
    Domain --> Layers
    Entry -.-> Common
```
