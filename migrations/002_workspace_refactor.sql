-- ============================================================
-- 迁移脚本: 子项目工作台重构
-- 日期: 2026-04-22
-- 说明: 新增 ProjectStatus 枚举、TargetStatus 新值、Photo 版本/确认字段
-- ============================================================

-- 1. TargetStatus 枚举新增 client_review（在 completed 之前）
-- 注意: PostgreSQL 中 ALTER TYPE ... ADD VALUE 不能在事务内执行
-- 如果在事务中运行，请先 COMMIT 再执行此行
ALTER TYPE target_status ADD VALUE IF NOT EXISTS 'client_review' BEFORE 'completed';

-- 2. 创建 project_status 枚举
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_status') THEN
    CREATE TYPE project_status AS ENUM ('not_started', 'shooting', 'retouching', 'completed');
  END IF;
END
$$;

-- 3. Project 表新增 project_status 字段
ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS project_status project_status NOT NULL DEFAULT 'not_started';

-- 4. Photo 表新增字段
ALTER TABLE photos
  ADD COLUMN IF NOT EXISTS parent_id BIGINT REFERENCES photos(id) ON DELETE SET NULL;

ALTER TABLE photos
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE photos
  ADD COLUMN IF NOT EXISTS is_confirmed BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE photos
  ADD COLUMN IF NOT EXISTS revision_notes TEXT;

-- 5. 索引（加速按 parent_id 查询精修版本）
CREATE INDEX IF NOT EXISTS idx_photos_parent_id ON photos(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_photos_is_confirmed ON photos(is_confirmed) WHERE is_confirmed = true;
