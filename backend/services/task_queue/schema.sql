-- task_queue SQLite Schema
-- 三张表：task_queue + scheduled_tasks + execution_history

-- 任务队列
CREATE TABLE IF NOT EXISTS task_queue (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    trigger_config TEXT NOT NULL DEFAULT '{}',
    generation_config TEXT NOT NULL,
    publish_config TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued',
    priority INTEGER NOT NULL DEFAULT 5,
    queue_position INTEGER,
    progress INTEGER NOT NULL DEFAULT 0,
    current_stage TEXT DEFAULT '',
    stage_detail TEXT DEFAULT '',
    output_url TEXT,
    output_word_count INTEGER,
    output_image_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    tags TEXT DEFAULT '[]',
    user_id TEXT
);

-- 定时任务配置
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    trigger_type TEXT NOT NULL,
    cron_expression TEXT,
    scheduled_at TIMESTAMP,
    timezone TEXT DEFAULT 'Asia/Shanghai',
    human_readable TEXT,
    generation_config TEXT NOT NULL,
    publish_config TEXT NOT NULL DEFAULT '{}',
    tags TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP
);

-- 执行历史
CREATE TABLE IF NOT EXISTS execution_history (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    triggered_by TEXT DEFAULT 'manual',
    output_url TEXT,
    output_summary TEXT,
    error TEXT,
    published INTEGER DEFAULT 0,
    publish_url TEXT
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tq_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_tq_priority ON task_queue(priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_eh_task ON execution_history(task_id);
CREATE INDEX IF NOT EXISTS idx_eh_time ON execution_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_st_enabled ON scheduled_tasks(enabled);
