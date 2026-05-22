<template>
  <div class="kanban-root">
    <!-- Left Icon Sidebar -->
    <aside class="icon-sidebar">
      <div class="sidebar-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="w-7 h-7">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.04l-.821 1.316z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
        </svg>
      </div>
      <nav class="sidebar-nav">
        <button v-for="icon in sidebarIcons" :key="icon.label" class="sidebar-btn" :class="{ active: icon.active }" :title="icon.label">
          <component :is="icon.svg" />
        </button>
      </nav>
      <div class="sidebar-bottom">
        <div class="avatar-ring">
          <img src="https://i.pravatar.cc/80?img=12" alt="avatar" class="avatar-img" />
        </div>
      </div>
    </aside>

    <!-- Main Area -->
    <div class="main-area">
      <!-- Top Navigation Bar -->
      <header class="top-nav">
        <div class="nav-left">
          <h1 class="nav-title">PhotoFlow Studio</h1>
          <span class="nav-divider" />
          <nav class="nav-tabs">
            <button v-for="tab in navTabs" :key="tab" class="nav-tab" :class="{ active: tab === 'Project Board' }">{{ tab }}</button>
          </nav>
        </div>
        <div class="nav-right">
          <div class="search-box">
            <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" /></svg>
            <span class="search-text">Search...</span>
            <span class="search-shortcut">⌘K</span>
          </div>
          <button class="icon-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" /></svg>
          </button>
        </div>
      </header>

      <!-- Workspace Header -->
      <div class="workspace-header">
        <div class="ws-left">
          <h2 class="ws-title">Commercial Product Shoot — Spring 2026</h2>
          <span class="ws-badge">{{ totalPhotos }} photos</span>
        </div>
        <div class="ws-right">
          <div class="ws-avatars">
            <img v-for="i in 3" :key="i" :src="`https://i.pravatar.cc/64?img=${i + 20}`" class="ws-avatar" :style="{ zIndex: 4 - i }" />
            <span class="ws-avatar-more">+2</span>
          </div>
        </div>
      </div>

      <!-- Kanban Board -->
      <div class="kanban-board">
        <!-- Originals Column -->
        <div class="kanban-col">
          <div class="col-header">
            <span class="col-dot dot-gray" />
            <h3 class="col-title">Originals</h3>
            <span class="col-count">{{ originals.length }}</span>
          </div>
          <div class="originals-grid">
            <div
              v-for="card in originals"
              :key="card.id"
              class="orig-card"
              :class="{
                'is-highlighted': hoveredSourceId === card.id,
                'is-in-use': card.inUse && hoveredSourceId !== card.id,
              }"
            >
              <div class="orig-img-wrap">
                <img :src="card.thumb" :alt="card.id" loading="lazy" class="orig-img" />
                <span v-if="card.inUse" class="in-use-badge">精修中</span>
              </div>
              <span class="orig-label">{{ card.id }}</span>
            </div>
          </div>
        </div>

        <!-- Retouched Column -->
        <div class="kanban-col col-retouched">
          <div class="col-header">
            <span class="col-dot dot-amber" />
            <h3 class="col-title">Retouched</h3>
            <span class="col-count">{{ retouched.length }}</span>
          </div>
          <div class="retouched-stack">
            <div
              v-for="card in retouched"
              :key="card.id"
              class="retouch-card"
              @mouseenter="hoveredSourceId = card.sourceRawId"
              @mouseleave="hoveredSourceId = null"
            >
              <div class="retouch-img-wrap">
                <img :src="card.thumb" :alt="card.id" loading="lazy" class="retouch-img" />
                <div class="retouch-overlay">
                  <span class="retouch-phase">RETOUCHED</span>
                </div>
              </div>
              <div class="retouch-info">
                <div class="retouch-id">{{ card.id }}</div>
                <div class="retouch-lineage">
                  <svg viewBox="0 0 16 16" fill="currentColor" class="lineage-icon"><path d="M8.75 3.75a.75.75 0 00-1.5 0v3.5h-3.5a.75.75 0 000 1.5h3.5v3.5a.75.75 0 001.5 0v-3.5h3.5a.75.75 0 000-1.5h-3.5v-3.5z" /></svg>
                  <span>source_raw_id: <strong>{{ card.sourceRawId }}</strong></span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Completed Column -->
        <div class="kanban-col col-completed">
          <div class="col-header">
            <span class="col-dot dot-green" />
            <h3 class="col-title">Completed</h3>
            <span class="col-count">{{ completed.length }}</span>
          </div>
          <div class="completed-stack">
            <div
              v-for="card in completed"
              :key="card.id"
              class="complete-card"
              @mouseenter="hoveredSourceId = card.sourceRawId"
              @mouseleave="hoveredSourceId = null"
            >
              <div class="complete-img-wrap">
                <img :src="card.thumb" :alt="card.id" loading="lazy" class="complete-img" />
                <div class="complete-badge">
                  <svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" /></svg>
                  <span>Delivered</span>
                </div>
              </div>
              <div class="complete-info">
                <div class="complete-id">{{ card.id }}</div>
                <div class="complete-meta">Final Export · sRGB · 300dpi</div>
                <div class="retouch-lineage">
                  <svg viewBox="0 0 16 16" fill="currentColor" class="lineage-icon"><circle cx="8" cy="8" r="3" /></svg>
                  <span>source_raw_id: <strong>{{ card.sourceRawId }}</strong></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'

const hoveredSourceId = ref<string | null>(null)

const navTabs = ['Project Board', 'Assets', 'Team', 'Settings']

const IconGrid = { render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', class: 'w-5 h-5' }, [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z' })]) }
const IconFolder = { render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', class: 'w-5 h-5' }, [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z' })]) }
const IconUsers = { render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', class: 'w-5 h-5' }, [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z' })]) }
const IconCog = { render: () => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '1.5', class: 'w-5 h-5' }, [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z' }), h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })]) }

const sidebarIcons = [
  { label: 'Board', svg: IconGrid, active: true },
  { label: 'Assets', svg: IconFolder, active: false },
  { label: 'Team', svg: IconUsers, active: false },
  { label: 'Settings', svg: IconCog, active: false },
]

interface OrigCard { id: string; thumb: string; inUse: boolean }
interface ProcessedCard { id: string; thumb: string; sourceRawId: string }

const originals = ref<OrigCard[]>([
  { id: 'RAW001', thumb: 'https://picsum.photos/seed/raw1/400/400', inUse: false },
  { id: 'RAW002', thumb: 'https://picsum.photos/seed/raw2/400/400', inUse: false },
  { id: 'RAW003', thumb: 'https://picsum.photos/seed/raw3/400/400', inUse: true },
  { id: 'RAW004', thumb: 'https://picsum.photos/seed/raw4/400/400', inUse: false },
  { id: 'RAW005', thumb: 'https://picsum.photos/seed/raw5/400/400', inUse: true },
  { id: 'RAW006', thumb: 'https://picsum.photos/seed/raw6/400/400', inUse: false },
  { id: 'RAW007', thumb: 'https://picsum.photos/seed/raw7/400/400', inUse: false },
  { id: 'RAW008', thumb: 'https://picsum.photos/seed/raw8/400/400', inUse: false },
])

const retouched = ref<ProcessedCard[]>([
  { id: 'RET001', thumb: 'https://picsum.photos/seed/watch1/600/800', sourceRawId: 'RAW003' },
  { id: 'RET002', thumb: 'https://picsum.photos/seed/shoe1/600/800', sourceRawId: 'RAW005' },
])

const completed = ref<ProcessedCard[]>([
  { id: 'FIN001', thumb: 'https://picsum.photos/seed/product1/800/1000', sourceRawId: 'RAW001' },
])

const totalPhotos = computed(() => originals.value.length + retouched.value.length + completed.value.length)
</script>

<style scoped>
/* ── Foundation ─────────────────────────────────── */
.kanban-root {
  display: flex;
  height: 100vh;
  background: #f8f9fb;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #1a1a2e;
  overflow: hidden;
}

/* ── Left Sidebar ──────────────────────────────── */
.icon-sidebar {
  width: 64px;
  background: #0f172a;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  flex-shrink: 0;
}
.sidebar-logo { color: #60a5fa; margin-bottom: 32px; }
.sidebar-nav { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.sidebar-btn {
  width: 40px; height: 40px; border-radius: 10px; border: none;
  background: transparent; color: #64748b; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.sidebar-btn:hover { background: #1e293b; color: #cbd5e1; }
.sidebar-btn.active { background: #1e40af; color: #fff; }
.sidebar-bottom { margin-top: auto; }
.avatar-ring {
  width: 36px; height: 36px; border-radius: 50%;
  border: 2px solid #334155; overflow: hidden;
}
.avatar-img { width: 100%; height: 100%; object-fit: cover; }

/* ── Main Area ─────────────────────────────────── */
.main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

/* ── Top Nav ───────────────────────────────────── */
.top-nav {
  height: 56px; background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; flex-shrink: 0;
}
.nav-left { display: flex; align-items: center; gap: 16px; }
.nav-title { font-size: 16px; font-weight: 700; letter-spacing: -0.3px; color: #0f172a; }
.nav-divider { width: 1px; height: 20px; background: #e2e8f0; }
.nav-tabs { display: flex; gap: 2px; }
.nav-tab {
  padding: 6px 14px; border-radius: 6px; border: none;
  background: transparent; font-size: 13px; color: #64748b;
  cursor: pointer; font-weight: 500; transition: all 0.15s;
}
.nav-tab:hover { background: #f1f5f9; color: #334155; }
.nav-tab.active { background: #eff6ff; color: #2563eb; font-weight: 600; }
.nav-right { display: flex; align-items: center; gap: 12px; }
.search-box {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; border-radius: 8px;
  background: #f8fafc; border: 1px solid #e2e8f0;
  font-size: 13px; color: #94a3b8; cursor: pointer;
}
.search-box:hover { border-color: #cbd5e1; }
.search-icon { width: 14px; height: 14px; }
.search-text { min-width: 60px; }
.search-shortcut {
  font-size: 11px; padding: 1px 5px; border-radius: 4px;
  background: #e2e8f0; color: #64748b; font-weight: 500;
}
.icon-btn {
  width: 36px; height: 36px; border-radius: 8px; border: 1px solid #e2e8f0;
  background: #fff; cursor: pointer; display: flex; align-items: center;
  justify-content: center; color: #475569; transition: all 0.15s;
}
.icon-btn:hover { background: #f1f5f9; }

/* ── Workspace Header ──────────────────────────── */
.workspace-header {
  padding: 20px 28px 0; display: flex;
  justify-content: space-between; align-items: center;
}
.ws-title { font-size: 20px; font-weight: 700; letter-spacing: -0.4px; }
.ws-badge {
  font-size: 12px; background: #eff6ff; color: #2563eb;
  padding: 3px 10px; border-radius: 12px; font-weight: 600;
  margin-left: 12px;
}
.ws-left { display: flex; align-items: center; }
.ws-right { display: flex; align-items: center; gap: 8px; }
.ws-avatars { display: flex; }
.ws-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  border: 2px solid #fff; margin-left: -8px; object-fit: cover;
}
.ws-avatar-more {
  width: 32px; height: 32px; border-radius: 50%;
  background: #e2e8f0; margin-left: -8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: #64748b;
  border: 2px solid #fff;
}

/* ── Kanban Board ──────────────────────────────── */
.kanban-board {
  display: grid;
  grid-template-columns: 2fr 1.5fr 1.5fr;
  gap: 20px;
  padding: 20px 28px 28px;
  flex: 1;
  overflow-y: auto;
  align-items: start;
}

/* ── Column Commons ────────────────────────────── */
.kanban-col {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.02);
  border: 1px solid #f0f0f0;
}
.col-header { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.col-dot { width: 10px; height: 10px; border-radius: 50%; }
.dot-gray { background: #94a3b8; }
.dot-amber { background: #f59e0b; }
.dot-green { background: #22c55e; }
.col-title { font-size: 14px; font-weight: 700; letter-spacing: -0.2px; }
.col-count {
  font-size: 11px; background: #f1f5f9; color: #64748b;
  padding: 2px 8px; border-radius: 8px; font-weight: 600;
  margin-left: auto;
}

/* ── Originals Grid ────────────────────────────── */
.originals-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.orig-card {
  border-radius: 12px;
  overflow: hidden;
  background: #f8fafc;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}
.orig-card.is-highlighted {
  box-shadow: 0 0 0 4px #3b82f6, 0 8px 25px rgba(59,130,246,0.25);
  transform: scale(1.05);
  z-index: 10;
  border-radius: 12px;
}
.orig-card.is-in-use {
  opacity: 0.55;
  filter: saturate(0.3);
}
.orig-img-wrap { position: relative; aspect-ratio: 1; overflow: hidden; }
.orig-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.in-use-badge {
  position: absolute; top: 6px; right: 6px;
  background: #2563eb; color: #fff;
  font-size: 10px; font-weight: 700;
  padding: 3px 8px; border-radius: 6px;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 8px rgba(37,99,235,0.4);
}
.orig-label {
  display: block; text-align: center;
  font-size: 11px; font-weight: 600; color: #64748b;
  padding: 6px 0;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* ── Retouched Stack ───────────────────────────── */
.retouched-stack { display: flex; flex-direction: column; gap: 14px; }
.retouch-card {
  border-radius: 14px; overflow: hidden;
  background: #fafbfc; border: 1px solid #f0f0f0;
  transition: all 0.2s;
  cursor: pointer;
}
.retouch-card:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}
.retouch-img-wrap { position: relative; aspect-ratio: 4/3; overflow: hidden; }
.retouch-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.retouch-overlay {
  position: absolute; top: 10px; left: 10px;
}
.retouch-phase {
  font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
  background: rgba(245,158,11,0.9); color: #fff;
  padding: 4px 10px; border-radius: 6px;
}
.retouch-info { padding: 12px 14px; }
.retouch-id { font-size: 13px; font-weight: 700; margin-bottom: 4px; }
.retouch-lineage {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #94a3b8;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.retouch-lineage strong { color: #3b82f6; font-weight: 700; }
.lineage-icon { width: 12px; height: 12px; color: #cbd5e1; flex-shrink: 0; }

/* ── Completed Stack ───────────────────────────── */
.completed-stack { display: flex; flex-direction: column; gap: 14px; }
.complete-card {
  border-radius: 14px; overflow: hidden;
  background: #fafbfc; border: 1px solid #f0f0f0;
  transition: all 0.2s;
  cursor: pointer;
}
.complete-card:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}
.complete-img-wrap { position: relative; aspect-ratio: 3/4; overflow: hidden; }
.complete-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.complete-badge {
  position: absolute; bottom: 12px; right: 12px;
  display: flex; align-items: center; gap: 4px;
  background: rgba(34,197,94,0.9); color: #fff;
  padding: 6px 12px; border-radius: 8px;
  font-size: 12px; font-weight: 700;
  box-shadow: 0 2px 8px rgba(34,197,94,0.3);
}
.complete-info { padding: 14px 16px; }
.complete-id { font-size: 14px; font-weight: 700; margin-bottom: 2px; }
.complete-meta { font-size: 11px; color: #94a3b8; margin-bottom: 6px; }

/* ── Utilities ─────────────────────────────────── */
.w-5 { width: 20px; }
.h-5 { height: 20px; }
.w-7 { width: 28px; }
.h-7 { height: 28px; }
.w-4 { width: 16px; }
.h-4 { height: 16px; }
</style>
