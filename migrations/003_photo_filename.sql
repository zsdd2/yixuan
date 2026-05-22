-- ============================================================
-- 迁移脚本 003: 照片原始文件名
-- 日期: 2026-04-22
-- 说明: Photo 表新增 original_filename 字段
-- ============================================================

ALTER TABLE photos
  ADD COLUMN IF NOT EXISTS original_filename TEXT;

-- 从 original_path 中提取文件名回填已有数据
UPDATE photos SET original_filename = regexp_replace(original_path, E'^.*[/\\\\]', '')
WHERE original_filename IS NULL;
