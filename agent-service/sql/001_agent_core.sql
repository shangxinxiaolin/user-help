-- Agent Service 核心数据表
-- 对应 app/db/models/ 包下的所有 SQLAlchemy ORM 模型

CREATE DATABASE IF NOT EXISTS lingxi_agent
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE lingxi_agent;

-- 1. 会话表
CREATE TABLE IF NOT EXISTS conversations (
    id BIGINT NOT NULL AUTO_INCREMENT,
    user_id VARCHAR(64) NOT NULL,
    status ENUM('进行中', '已转人工', '已结束')
        NOT NULL DEFAULT '进行中',
    summary TEXT NULL,
    summary_upto_msg_id BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_conversations_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 2. 消息表
CREATE TABLE IF NOT EXISTS messages (
    id BIGINT NOT NULL AUTO_INCREMENT,
    conversation_id BIGINT NOT NULL,
    role ENUM('user', 'assistant', 'tool') NOT NULL,
    content TEXT NULL,
    tool_calls JSON NULL,
    tool_call_id VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_messages_conversation_id (conversation_id),
    CONSTRAINT fk_messages_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES conversations (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 3. 工具审计表 (SPEC 1.5.7)
CREATE TABLE IF NOT EXISTS tool_audit_logs (
    id BIGINT NOT NULL AUTO_INCREMENT,
    conversation_id BIGINT NULL,
    tool_call_id VARCHAR(64) NOT NULL,
    tool_name VARCHAR(64) NOT NULL,
    tool_source VARCHAR(32) NOT NULL DEFAULT 'builtin',
    mcp_server VARCHAR(64) NULL,
    arguments JSON NULL,
    result_summary TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT '成功',
    error_message TEXT NULL,
    retry_count INT NOT NULL DEFAULT 0,
    duration_ms INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_tool_audit_conversation_id (conversation_id),
    KEY ix_tool_audit_tool_name (tool_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 4. 知识飞轮待审队列 (SPEC 1.5.2)
CREATE TABLE IF NOT EXISTS review_queue (
    id BIGINT NOT NULL AUTO_INCREMENT,
    normalized_question VARCHAR(512) NOT NULL,
    ai_suggested_answer TEXT NULL,
    occurrence_count INT NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    reviewed_answer TEXT NULL,
    reviewed_by VARCHAR(64) NULL,
    reviewed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_review_queue_normalized (normalized_question)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 5. 低置信度问题池 (SPEC 1.5.1 / 1.5.2)
CREATE TABLE IF NOT EXISTS low_confidence_questions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    conversation_id BIGINT NULL,
    raw_question TEXT NOT NULL,
    intent VARCHAR(64) NULL,
    evidence_confidence FLOAT NOT NULL DEFAULT 0.0,
    source VARCHAR(32) NOT NULL DEFAULT 'evidence_confidence',
    matched_review_id BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_low_conf_conversation_id (conversation_id),
    KEY ix_low_conf_matched_review_id (matched_review_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 6. 知识块表 (SPEC 1.5.2 / 5.1)
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id BIGINT NOT NULL AUTO_INCREMENT,
    title VARCHAR(256) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(64) NOT NULL DEFAULT '通用',
    is_key_clause BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(64) NOT NULL DEFAULT 'manual',
    milvus_id VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_knowledge_chunks_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 7. 对话挖知识暂存表 (SPEC 1.5.3)
CREATE TABLE IF NOT EXISTS qa_extraction_staging (
    id BIGINT NOT NULL AUTO_INCREMENT,
    conversation_id BIGINT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'extracted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_qa_staging_fingerprint (fingerprint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 8. 评估记录表 (SPEC 1.5.4)
CREATE TABLE IF NOT EXISTS eval_runs (
    id BIGINT NOT NULL AUTO_INCREMENT,
    strategy VARCHAR(64) NOT NULL,
    recall_rate FLOAT NOT NULL DEFAULT 0.0,
    coverage_rate FLOAT NOT NULL DEFAULT 0.0,
    faithful_rate FLOAT NOT NULL DEFAULT 0.0,
    total_cases INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 9. 忠实度个案台账表 (SPEC 1.5.4)
CREATE TABLE IF NOT EXISTS faith_cases (
    id BIGINT NOT NULL AUTO_INCREMENT,
    question TEXT NOT NULL,
    evidence TEXT NULL,
    answer TEXT NOT NULL,
    judge_reason TEXT NULL,
    seen_count INT NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- 10. 主题分类记录表 (SPEC 1.5.6)
CREATE TABLE IF NOT EXISTS topic_classifications (
    id BIGINT NOT NULL AUTO_INCREMENT,
    question_id BIGINT NULL,
    raw_question TEXT NOT NULL,
    topics JSON NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    classified_by VARCHAR(32) NOT NULL DEFAULT 'llm',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY ix_topic_question_id (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;
