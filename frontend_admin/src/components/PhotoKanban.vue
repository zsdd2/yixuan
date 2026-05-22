<template>
  <div class="pk-root">
    <!-- 三列看板 -->
    <div class="pk-board">
      <!-- ═══ 第一列：原图 ═══ -->
      <div class="pk-col">
        <div class="pk-col-head">
          <span class="pk-dot" style="background:#94a3b8" />
          <span class="pk-col-title">原图 Originals</span>
          <span class="pk-col-count">{{ visibleRaws.length }}</span>
        </div>

        <div class="pk-col-body">
          <!-- 已选中 / 被筛选命中的原图 -->
          <div
            v-for="raw in visibleRaws"
            :key="raw.id"
            class="raw-card"
            :class="{
              'is-active': activeFilter === raw.id,
              'is-selected': selectedRawIds.has(raw.id) && !activeFilter,
            }"
            @click="onCardClick(raw.id)"
          >
            <div class="raw-thumb-wrap">
              <img :src="raw.thumb" loading="lazy" class="raw-thumb" />
              <span v-if="raw.inUse && activeFilter !== raw.id" class="raw-badge-inuse">精修中</span>
            </div>
            <div class="raw-meta">
              <span class="raw-tag">#{{ raw.id }}</span>
              <span class="raw-file">{{ raw.filename }}</span>
            </div>
            <button
              v-if="!activeFilter"
              class="raw-check"
              :class="{ checked: selectedRawIds.has(raw.id) }"
              @click.stop="toggleSelect(raw.id)"
            >
              <svg v-if="selectedRawIds.has(raw.id)" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd" /></svg>
            </button>
          </div>

          <!-- 折叠归拢提示 -->
          <button
            v-if="collapsedCount > 0"
            class="collapsed-hint"
            @click="expandAll"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5 hint-arrow" :class="{ rotated: showAllRaws }"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" /></svg>
            <span v-if="!showAllRaws">展开其余 {{ collapsedCount }} 张未选中原图</span>
            <span v-else>收起未选中原图</span>
          </button>
        </div>
      </div>

      <!-- ═══ 第二列：精修图 ═══ -->
      <div class="pk-col">
        <div class="pk-col-head">
          <span class="pk-dot" style="background:#f59e0b" />
          <span class="pk-col-title">精修 Retouched</span>
          <span class="pk-col-count">{{ visibleRetouched.length }}</span>
          <button class="pk-add-btn" @click="openAddDialog('retouched')">+ 添加</button>
        </div>

        <div class="pk-col-body">
          <div
            v-for="photo in visibleRetouched"
            :key="photo.id"
            class="proc-card"
            :class="{ 'is-active': activeFilter === photo.sourceRawId }"
            @click="onCardClick(photo.sourceRawId)"
          >
            <div class="proc-thumb-wrap">
              <img :src="photo.thumb" loading="lazy" class="proc-thumb" />
              <span class="proc-phase-tag phase-retouched">RETOUCHED</span>
            </div>
            <div class="proc-meta">
              <div class="proc-id">{{ photo.id }}</div>
              <div class="proc-lineage">
                <span class="lineage-dot" style="background:#3b82f6" />
                源: <strong>#{{ photo.sourceRawId }}</strong>
              </div>
            </div>
          </div>

          <div v-if="visibleRetouched.length === 0" class="pk-empty">
            <span>{{ activeFilter ? '该原图暂无精修图' : '暂无精修图' }}</span>
          </div>
        </div>
      </div>

      <!-- ═══ 第三列：完成图 ═══ -->
      <div class="pk-col">
        <div class="pk-col-head">
          <span class="pk-dot" style="background:#22c55e" />
          <span class="pk-col-title">完成 Completed</span>
          <span class="pk-col-count">{{ visibleCompleted.length }}</span>
          <button class="pk-add-btn" @click="openAddDialog('completed')">+ 添加</button>
        </div>

        <div class="pk-col-body">
          <div
            v-for="photo in visibleCompleted"
            :key="photo.id"
            class="proc-card proc-card-lg"
            :class="{ 'is-active': activeFilter === photo.sourceRawId }"
            @click="onCardClick(photo.sourceRawId)"
          >
            <div class="proc-thumb-wrap proc-thumb-lg">
              <img :src="photo.thumb" loading="lazy" class="proc-thumb" />
              <span class="proc-phase-tag phase-completed">
                <svg viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" /></svg>
                FINAL
              </span>
            </div>
            <div class="proc-meta">
              <div class="proc-id">{{ photo.id }}</div>
              <div class="proc-detail">Final Export · sRGB · 300dpi</div>
              <div class="proc-lineage">
                <span class="lineage-dot" style="background:#22c55e" />
                源: <strong>#{{ photo.sourceRawId }}</strong>
              </div>
            </div>
          </div>

          <div v-if="visibleCompleted.length === 0" class="pk-empty">
            <span>{{ activeFilter ? '该原图暂无完成图' : '暂无完成图' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 全局筛选指示条 -->
    <transition name="filter-bar">
      <div v-if="activeFilter" class="pk-filter-bar">
        <span class="filter-label">当前溯源筛选：</span>
        <span class="filter-tag">#{{ activeFilter }}</span>
        <button class="filter-clear" @click="activeFilter = null">
          <svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4"><path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" /></svg>
          清除筛选
        </button>
      </div>
    </transition>

    <!-- 添加弹窗 -->
    <div v-if="showAddDialog" class="pk-dialog-mask" @click.self="showAddDialog = false">
      <div class="pk-dialog">
        <div class="pk-dialog-head">
          <span>{{ addDialogType === 'retouched' ? '添加精修图' : '添加完成图' }}</span>
          <button class="pk-dialog-close" @click="showAddDialog = false">×</button>
        </div>
        <div class="pk-dialog-body">
          <label class="pk-dialog-label">请选择绑定的原图标签编号</label>
          <select v-model="addDialogSelectedRaw" class="pk-dialog-select">
            <option value="" disabled>— 选择原图标签 —</option>
            <option v-for="raw in allRaws" :key="raw.id" :value="raw.id">#{{ raw.id }} · {{ raw.filename }}</option>
          </select>
          <div class="pk-dialog-hint">
            入库必须绑定原图标签，以确保照片处理的完整溯源链路。
          </div>
        </div>
        <div class="pk-dialog-foot">
          <button class="btn-cancel" @click="showAddDialog = false">取消</button>
          <button class="btn-confirm" :disabled="!addDialogSelectedRaw" @click="confirmAdd">
            确认绑定并上传
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps<{ projectId: string | number }>()

// ── Mock Data ──────────────────────────────────────────
interface RawPhoto {
  id: string
  filename: string
  thumb: string
  inUse: boolean
}
interface ProcessedPhoto {
  id: string
  thumb: string
  sourceRawId: string
}

const allRaws = ref<RawPhoto[]>([
  { id: 'RAW-001', filename: 'DSC_4021.ARW', thumb: 'https://picsum.photos/seed/r1/400/400', inUse: true },
  { id: 'RAW-002', filename: 'DSC_4022.ARW', thumb: 'https://picsum.photos/seed/r2/400/400', inUse: true },
  { id: 'RAW-003', filename: 'DSC_4023.ARW', thumb: 'https://picsum.photos/seed/r3/400/400', inUse: false },
  { id: 'RAW-004', filename: 'DSC_4024.ARW', thumb: 'https://picsum.photos/seed/r4/400/400', inUse: false },
  { id: 'RAW-005', filename: 'DSC_4025.ARW', thumb: 'https://picsum.photos/seed/r5/400/400', inUse: false },
  { id: 'RAW-006', filename: 'DSC_4026.ARW', thumb: 'https://picsum.photos/seed/r6/400/400', inUse: false },
  { id: 'RAW-007', filename: 'DSC_4027.ARW', thumb: 'https://picsum.photos/seed/r7/400/400', inUse: false },
  { id: 'RAW-008', filename: 'DSC_4028.ARW', thumb: 'https://picsum.photos/seed/r8/400/400', inUse: false },
])

const allRetouched = ref<ProcessedPhoto[]>([
  { id: 'RET-001', thumb: 'https://picsum.photos/seed/ret1/600/800', sourceRawId: 'RAW-001' },
  { id: 'RET-002', thumb: 'https://picsum.photos/seed/ret2/600/800', sourceRawId: 'RAW-001' },
  { id: 'RET-003', thumb: 'https://picsum.photos/seed/ret3/600/800', sourceRawId: 'RAW-002' },
])

const allCompleted = ref<ProcessedPhoto[]>([
  { id: 'FIN-001', thumb: 'https://picsum.photos/seed/fin1/800/1000', sourceRawId: 'RAW-001' },
  { id: 'FIN-002', thumb: 'https://picsum.photos/seed/fin2/800/1000', sourceRawId: 'RAW-002' },
])

// ── State ──────────────────────────────────────────────
const selectedRawIds = ref(new Set(['RAW-001', 'RAW-002', 'RAW-003']))
const activeFilter = ref<string | null>(null)
const showAllRaws = ref(false)

// ── Computed: visible lists ────────────────────────────
const visibleRaws = computed(() => {
  if (activeFilter.value) {
    return allRaws.value.filter(r => r.id === activeFilter.value)
  }
  const selected = allRaws.value.filter(r => selectedRawIds.value.has(r.id))
  if (showAllRaws.value) return allRaws.value
  return selected
})

const collapsedCount = computed(() => {
  if (activeFilter.value) return 0
  if (showAllRaws.value) return 0
  return allRaws.value.length - selectedRawIds.value.size
})

const visibleRetouched = computed(() => {
  if (activeFilter.value) {
    return allRetouched.value.filter(p => p.sourceRawId === activeFilter.value)
  }
  return allRetouched.value.filter(p => selectedRawIds.value.has(p.sourceRawId))
})

const visibleCompleted = computed(() => {
  if (activeFilter.value) {
    return allCompleted.value.filter(p => p.sourceRawId === activeFilter.value)
  }
  return allCompleted.value.filter(p => selectedRawIds.value.has(p.sourceRawId))
})

// ── Interactions ───────────────────────────────────────
function onCardClick(rawId: string) {
  if (activeFilter.value === rawId) {
    activeFilter.value = null
  } else {
    activeFilter.value = rawId
  }
}

function toggleSelect(rawId: string) {
  const s = new Set(selectedRawIds.value)
  if (s.has(rawId)) s.delete(rawId)
  else s.add(rawId)
  selectedRawIds.value = s
}

function expandAll() {
  showAllRaws.value = !showAllRaws.value
}

// ── Add dialog ─────────────────────────────────────────
const showAddDialog = ref(false)
const addDialogType = ref<'retouched' | 'completed'>('retouched')
const addDialogSelectedRaw = ref('')

function openAddDialog(type: 'retouched' | 'completed') {
  addDialogType.value = type
  addDialogSelectedRaw.value = activeFilter.value || ''
  showAddDialog.value = true
}

function confirmAdd() {
  ElMessage.success(`已绑定 #${addDialogSelectedRaw.value}，请选择文件上传`)
  showAddDialog.value = false
}
</script>

<style scoped>
.pk-root {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8f9fb;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── Board ────────────────────────────────────── */
.pk-board {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  overflow: hidden;
}
.pk-col {
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e5e7eb;
  overflow: hidden;
}
.pk-col:last-child { border-right: none; }

.pk-col-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 18px 12px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
  background: #fff;
}
.pk-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.pk-col-title { font-size: 13px; font-weight: 700; color: #1e293b; letter-spacing: -0.2px; }
.pk-col-count {
  font-size: 11px; background: #f1f5f9; color: #64748b;
  padding: 2px 8px; border-radius: 8px; font-weight: 600;
}
.pk-add-btn {
  margin-left: auto; border: 1px dashed #d1d5db;
  background: transparent; color: #6b7280; font-size: 12px; font-weight: 500;
  padding: 4px 12px; border-radius: 6px; cursor: pointer;
  transition: all 0.15s;
}
.pk-add-btn:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }

.pk-col-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pk-col-body::-webkit-scrollbar { width: 4px; }
.pk-col-body::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }

/* ── Raw Cards ────────────────────────────────── */
.raw-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 12px;
  background: #fff;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}
.raw-card:hover { background: #f8fafc; }
.raw-card.is-selected {
  border-color: #bfdbfe;
  background: #eff6ff;
}
.raw-card.is-active {
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15), 0 4px 12px rgba(59,130,246,0.1);
  transform: scale(1.02);
}

.raw-thumb-wrap {
  width: 56px; height: 56px;
  border-radius: 8px; overflow: hidden;
  flex-shrink: 0; position: relative;
}
.raw-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.raw-badge-inuse {
  position: absolute; top: 3px; right: 3px;
  background: #2563eb; color: #fff;
  font-size: 9px; font-weight: 700;
  padding: 2px 5px; border-radius: 4px;
  line-height: 1;
}

.raw-meta { flex: 1; min-width: 0; }
.raw-tag {
  display: block;
  font-size: 13px; font-weight: 700; color: #1e293b;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.raw-file {
  display: block;
  font-size: 11px; color: #94a3b8;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.raw-check {
  width: 22px; height: 22px; border-radius: 6px;
  border: 2px solid #d1d5db; background: #fff;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  color: #fff; flex-shrink: 0; transition: all 0.15s;
}
.raw-check.checked {
  background: #3b82f6; border-color: #3b82f6;
}

/* ── Collapsed hint ───────────────────────────── */
.collapsed-hint {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 12px;
  border-radius: 8px; border: 1px dashed #e2e8f0;
  background: transparent; color: #94a3b8;
  font-size: 12px; cursor: pointer;
  transition: all 0.15s;
}
.collapsed-hint:hover { background: #f8fafc; color: #64748b; border-color: #cbd5e1; }
.hint-arrow { transition: transform 0.2s; flex-shrink: 0; }
.hint-arrow.rotated { transform: rotate(90deg); }

/* ── Processed Cards (retouched + completed) ── */
.proc-card {
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.proc-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  transform: translateY(-1px);
}
.proc-card.is-active {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15), 0 4px 16px rgba(59,130,246,0.08);
}

.proc-thumb-wrap { position: relative; aspect-ratio: 4/3; overflow: hidden; }
.proc-card-lg .proc-thumb-wrap { aspect-ratio: 3/4; }
.proc-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }

.proc-phase-tag {
  position: absolute; top: 8px; left: 8px;
  font-size: 10px; font-weight: 700; letter-spacing: 1px;
  padding: 4px 10px; border-radius: 6px; color: #fff;
  display: flex; align-items: center; gap: 4px;
}
.phase-retouched { background: rgba(245,158,11,0.85); }
.phase-completed { background: rgba(34,197,94,0.85); }

.proc-meta { padding: 10px 14px; }
.proc-id { font-size: 13px; font-weight: 700; color: #1e293b; margin-bottom: 2px; }
.proc-detail { font-size: 11px; color: #94a3b8; margin-bottom: 4px; }
.proc-lineage {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: #94a3b8;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.proc-lineage strong { color: #3b82f6; font-weight: 700; }
.lineage-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

.pk-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: #c0c4cc; padding: 40px 0;
}

/* ── Filter Bar ───────────────────────────────── */
.pk-filter-bar {
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 10px;
  background: #0f172a; color: #fff;
  padding: 10px 20px; border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  font-size: 13px; z-index: 20;
}
.filter-label { color: #94a3b8; }
.filter-tag {
  font-weight: 700; font-family: 'SF Mono', monospace;
  background: #1e40af; padding: 3px 10px; border-radius: 6px;
}
.filter-clear {
  display: flex; align-items: center; gap: 4px;
  border: 1px solid #334155; background: transparent;
  color: #cbd5e1; padding: 4px 12px; border-radius: 6px;
  font-size: 12px; cursor: pointer; transition: all 0.15s;
}
.filter-clear:hover { background: #1e293b; border-color: #475569; }

.filter-bar-enter-active,
.filter-bar-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.filter-bar-enter-from,
.filter-bar-leave-to { opacity: 0; transform: translateX(-50%) translateY(20px); }

/* ── Add Dialog ───────────────────────────────── */
.pk-dialog-mask {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.3); backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center;
}
.pk-dialog {
  width: 420px; background: #fff;
  border-radius: 16px; overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.pk-dialog-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 18px 22px; border-bottom: 1px solid #f0f0f0;
  font-size: 15px; font-weight: 700;
}
.pk-dialog-close {
  width: 28px; height: 28px; border-radius: 8px;
  border: none; background: #f1f5f9; color: #64748b;
  font-size: 18px; cursor: pointer; transition: all 0.15s;
}
.pk-dialog-close:hover { background: #e2e8f0; }
.pk-dialog-body { padding: 22px; }
.pk-dialog-label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 8px; }
.pk-dialog-select {
  width: 100%; padding: 10px 12px; border: 1px solid #d1d5db;
  border-radius: 10px; font-size: 13px; background: #fff;
  color: #1e293b; outline: none; appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3E%3Cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3E%3C/svg%3E");
  background-position: right 10px center;
  background-repeat: no-repeat;
  background-size: 16px;
}
.pk-dialog-select:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
.pk-dialog-hint {
  margin-top: 12px; font-size: 12px; color: #94a3b8;
  padding: 10px 12px; background: #f8fafc; border-radius: 8px;
  line-height: 1.5;
}
.pk-dialog-foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 14px 22px; border-top: 1px solid #f0f0f0;
}
.btn-cancel {
  padding: 8px 18px; border: 1px solid #d1d5db; border-radius: 8px;
  background: #fff; color: #374151; font-size: 13px; cursor: pointer;
}
.btn-cancel:hover { background: #f9fafb; }
.btn-confirm {
  padding: 8px 18px; border: none; border-radius: 8px;
  background: #2563eb; color: #fff; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: background 0.15s;
}
.btn-confirm:hover { background: #1d4ed8; }
.btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Utilities ────────────────────────────────── */
.w-3\.5 { width: 14px; height: 14px; }
.w-4 { width: 16px; height: 16px; }
.h-4 { height: 16px; }
</style>
