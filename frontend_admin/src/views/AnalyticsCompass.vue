<template>
  <div class="compass-page">
    <header class="compass-header">
      <div class="title-group">
        <h1>数据罗盘</h1>
        <span>经营和生产总览</span>
      </div>
      <div class="filters">
        <el-select v-model="filter.year" class="filter-select year" @change="fetchCompass">
          <el-option v-for="year in yearOptions" :key="year" :label="`${year}年`" :value="year" />
        </el-select>
        <el-select v-model="filter.month" class="filter-select month" @change="fetchCompass">
          <el-option label="全年" :value="0" />
          <el-option v-for="m in 12" :key="m" :label="`${m}月`" :value="m" />
        </el-select>
        <el-select v-model="filter.client_id" class="filter-select client" clearable placeholder="全部客户" @change="fetchCompass">
          <el-option v-for="client in filters.clients" :key="client.id" :label="client.name" :value="client.id" />
        </el-select>
        <el-select v-model="filter.shooting_type" class="filter-select shooting" clearable placeholder="全部拍摄类型" @change="fetchCompass">
          <el-option v-for="type in filters.shooting_types" :key="type" :label="type" :value="type" />
        </el-select>
        <el-button class="refresh-button" :loading="loading" @click="fetchCompass">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <section class="metric-grid" v-loading="loading">
      <div v-for="metric in metrics" :key="metric.key" class="metric-card">
        <div class="metric-icon" :class="metric.tone">
          <el-icon><component :is="metric.icon" /></el-icon>
        </div>
        <div class="metric-copy">
          <div class="metric-label">{{ metric.label }}</div>
          <div class="metric-value" :class="metric.tone">{{ metric.prefix }}{{ metric.value }}<small>{{ metric.unit }}</small></div>
          <div class="metric-rate">
            较去年
            <span v-if="metric.rate !== null" :class="metric.rate >= 0 ? 'up' : 'down'">
              {{ metric.rate >= 0 ? '↑' : '↓' }} {{ Math.abs(metric.rate).toFixed(1) }}%
            </span>
            <span v-else>--</span>
          </div>
        </div>
      </div>
    </section>

    <section class="panel work-panel">
      <div class="section-header">工作进度</div>
      <div class="work-grid">
        <div class="sub-panel">
          <h3>项目状态分布</h3>
          <div ref="statusChartRef" class="chart status-chart"></div>
        </div>
        <div class="sub-panel progress-panel">
          <h3>白图/场景图完成进度</h3>
          <div class="progress-item">
            <div class="progress-title">
              <span>白图总数 / 完成数</span>
              <b><em>{{ work.white_total }}</em> / {{ work.white_completed }}</b>
              <small>完成率 {{ percent(work.white_completed, work.white_total) }}%</small>
            </div>
            <el-progress :percentage="percent(work.white_completed, work.white_total)" :show-text="false" />
            <div class="progress-scale">
              <span>0</span><span>{{ work.white_completed }}</span><span>{{ work.white_total }}</span>
            </div>
          </div>
          <div class="progress-item">
            <div class="progress-title">
              <span>场景图总数 / 完成数</span>
              <b><em>{{ work.scene_total }}</em> / {{ work.scene_completed }}</b>
              <small>完成率 {{ percent(work.scene_completed, work.scene_total) }}%</small>
            </div>
            <el-progress :percentage="percent(work.scene_completed, work.scene_total)" :show-text="false" />
            <div class="progress-scale">
              <span>0</span><span>{{ work.scene_completed }}</span><span>{{ work.scene_total }}</span>
            </div>
          </div>
        </div>
        <div class="sub-panel stage-panel">
          <h3>照片阶段统计</h3>
          <div class="stage-row">
            <div class="stage-item blue">
              <div class="stage-icon"><el-icon><Picture /></el-icon></div>
              <span>原图</span>
              <b>{{ formatNumber(work.raw_photo_count) }}<small>张</small></b>
            </div>
            <div class="stage-divider"></div>
            <div class="stage-item green">
              <div class="stage-icon"><el-icon><MagicStick /></el-icon></div>
              <span>精修图</span>
              <b>{{ formatNumber(work.retouched_photo_count) }}<small>张</small></b>
            </div>
            <div class="stage-divider"></div>
            <div class="stage-item purple">
              <div class="stage-icon"><el-icon><PictureFilled /></el-icon></div>
              <span>最终图</span>
              <b>{{ formatNumber(work.final_photo_count) }}<small>张</small></b>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="panel trend-panel">
      <div class="section-header">年度趋势</div>
      <div class="trend-grid">
        <div class="sub-panel trend-sub">
          <h3>月度产出趋势 <span>（最终成图张数 / 完成项目数 / 白图&场景图拆分）</span></h3>
          <div ref="outputChartRef" class="chart trend-chart"></div>
        </div>
        <div class="sub-panel trend-sub">
          <h3>月度收入趋势 <span>（应收 / 已收 / 未收）</span></h3>
          <div ref="incomeChartRef" class="chart trend-chart"></div>
        </div>
      </div>
    </section>

    <section class="panel client-panel">
      <div class="section-header">客户经营</div>
      <div class="client-grid">
        <div class="sub-panel table-panel">
          <h3>客户消费排行</h3>
          <table>
            <thead>
              <tr>
                <th>客户名称</th><th>项目数</th><th>应收金额</th><th>已收金额</th><th>未收金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in clientBusiness.consumption_ranking" :key="row.client_id">
                <td>{{ index + 1 }}　{{ row.client_name }}</td>
                <td>{{ row.project_count }}</td>
                <td>¥{{ formatNumber(row.receivable_amount) }}</td>
                <td>¥{{ formatNumber(row.received_amount) }}</td>
                <td class="danger">¥{{ formatNumber(row.unreceived_amount) }}</td>
              </tr>
              <tr v-if="clientBusiness.consumption_ranking.length === 0"><td colspan="5" class="empty">暂无数据</td></tr>
            </tbody>
          </table>
          <div class="table-more">查看全部 〉</div>
        </div>
        <div class="sub-panel table-panel">
          <h3>
            <span class="tab-active">客户产出排行</span>
            <span class="tab-muted">客户项目数排行</span>
          </h3>
          <table>
            <thead>
              <tr>
                <th>客户名称</th><th>最终成图数</th><th>白图最终图</th><th>场景图最终图</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in clientBusiness.output_ranking" :key="row.client_id">
                <td>{{ index + 1 }}　{{ row.client_name }}</td>
                <td>{{ formatNumber(row.final_photo_count) }}</td>
                <td>{{ formatNumber(row.white_final_count) }}</td>
                <td>{{ formatNumber(row.scene_final_count) }}</td>
              </tr>
              <tr v-if="clientBusiness.output_ranking.length === 0"><td colspan="4" class="empty">暂无数据</td></tr>
            </tbody>
          </table>
          <div class="table-more">查看全部 〉</div>
        </div>
        <div class="sub-panel alert-panel">
          <h3>未收款提醒 <span>更多〉</span></h3>
          <div class="alert-list">
            <div v-for="alert in clientBusiness.payment_alerts" :key="alert.project_id" class="alert-item">
              <div class="alert-icon">¥</div>
              <div class="alert-body">
                <b>{{ alert.client_name }} · {{ alert.project_name }}</b>
                <p>已确认账单 ¥{{ formatNumber(alert.amount) }}</p>
              </div>
              <time>{{ formatDate(alert.confirmed_at) }}</time>
            </div>
            <div v-if="clientBusiness.payment_alerts.length === 0" class="empty-alert">
              暂无未收款提醒
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import type { Component } from 'vue'
import type { ECharts } from 'echarts/core'
import {
  Clock,
  FolderChecked,
  MagicStick,
  Money,
  Picture,
  PictureFilled,
  Refresh,
  Wallet,
  Warning,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

type OverviewMetric = { value: number; year_over_year_rate: number | null }
type ChartInstance = ECharts | null
type InitChart = (el: HTMLElement) => ECharts

interface CompassData {
  filters: {
    year: number
    clients: { id: number; name: string }[]
    shooting_types: string[]
  }
  overview: {
    completed_projects: OverviewMetric
    active_projects: OverviewMetric
    monthly_final_photos: OverviewMetric
    receivable_amount: OverviewMetric
    received_amount: OverviewMetric
    unreceived_amount: OverviewMetric
  }
  work_progress: {
    project_status_distribution: { status: string; label: string; count: number }[]
    white_total: number
    white_completed: number
    scene_total: number
    scene_completed: number
    raw_photo_count: number
    retouched_photo_count: number
    final_photo_count: number
  }
  annual_trends: {
    monthly_output: {
      months: number[]
      white_final: number[]
      scene_final: number[]
      final_total: number[]
      completed_projects: number[]
    }
    monthly_income: {
      months: number[]
      receivable: number[]
      received: number[]
      unreceived: number[]
    }
  }
  client_business: {
    consumption_ranking: {
      client_id: number
      client_name: string
      project_count: number
      receivable_amount: number
      received_amount: number
      unreceived_amount: number
    }[]
    output_ranking: {
      client_id: number
      client_name: string
      final_photo_count: number
      white_final_count: number
      scene_final_count: number
    }[]
    payment_alerts: {
      project_id: number
      project_name: string
      client_name: string
      amount: number
      confirmed_at: string | null
    }[]
  }
}

const now = new Date()
const yearOptions = Array.from({ length: 7 }, (_, i) => now.getFullYear() - 4 + i)
const loading = ref(false)
const filter = reactive({
  year: now.getFullYear(),
  month: 0,
  client_id: undefined as number | undefined,
  shooting_type: undefined as string | undefined,
})

const filters = reactive<CompassData['filters']>({ year: now.getFullYear(), clients: [], shooting_types: [] })
const overview = reactive<CompassData['overview']>({
  completed_projects: { value: 0, year_over_year_rate: null },
  active_projects: { value: 0, year_over_year_rate: null },
  monthly_final_photos: { value: 0, year_over_year_rate: null },
  receivable_amount: { value: 0, year_over_year_rate: null },
  received_amount: { value: 0, year_over_year_rate: null },
  unreceived_amount: { value: 0, year_over_year_rate: null },
})
const work = reactive<CompassData['work_progress']>({
  project_status_distribution: [],
  white_total: 0,
  white_completed: 0,
  scene_total: 0,
  scene_completed: 0,
  raw_photo_count: 0,
  retouched_photo_count: 0,
  final_photo_count: 0,
})
const annual = reactive<CompassData['annual_trends']>({
  monthly_output: { months: [], white_final: [], scene_final: [], final_total: [], completed_projects: [] },
  monthly_income: { months: [], receivable: [], received: [], unreceived: [] },
})
const clientBusiness = reactive<CompassData['client_business']>({
  consumption_ranking: [],
  output_ranking: [],
  payment_alerts: [],
})

const statusChartRef = ref<HTMLDivElement>()
const outputChartRef = ref<HTMLDivElement>()
const incomeChartRef = ref<HTMLDivElement>()
let statusChart: ChartInstance = null
let outputChart: ChartInstance = null
let incomeChart: ChartInstance = null
let resizeObserver: ResizeObserver | null = null
let initChart: InitChart | null = null
let chartCorePromise: Promise<void> | null = null

const metrics = computed(() => [
  metric('completed_projects', '完成项目', FolderChecked, overview.completed_projects, '', '', 'blue'),
  metric('active_projects', '进行中项目', Clock, overview.active_projects, '', '', 'blue'),
  metric('monthly_final_photos', '本月最终成图', Picture, overview.monthly_final_photos, '', '张', 'blue'),
  metric('receivable_amount', '应收金额', Wallet, overview.receivable_amount, '¥', '', 'blue'),
  metric('received_amount', '已收金额', Money, overview.received_amount, '¥', '', 'green'),
  metric('unreceived_amount', '未收金额', Warning, overview.unreceived_amount, '¥', '', 'orange'),
])

function metric(key: string, label: string, icon: Component, source: OverviewMetric, prefix: string, unit: string, tone: string) {
  return {
    key,
    label,
    icon: markRaw(icon),
    value: formatNumber(source.value),
    rate: source.year_over_year_rate,
    prefix,
    unit,
    tone,
  }
}

async function fetchCompass() {
  loading.value = true
  try {
    const params: Record<string, any> = { year: filter.year }
    if (filter.month) params.month = filter.month
    if (filter.client_id) params.client_id = filter.client_id
    if (filter.shooting_type) params.shooting_type = filter.shooting_type
    const data = await request.get<CompassData>('/api/v1/analytics/compass', params)
    Object.assign(filters, data.filters)
    Object.assign(overview, data.overview)
    Object.assign(work, data.work_progress)
    Object.assign(annual.monthly_output, data.annual_trends.monthly_output)
    Object.assign(annual.monthly_income, data.annual_trends.monthly_income)
    Object.assign(clientBusiness, data.client_business)
    await nextTick()
    await renderCharts()
  } catch (e: any) {
    ElMessage.error(e.message || '数据罗盘加载失败')
  } finally {
    loading.value = false
  }
}

async function ensureChartCore() {
  if (chartCorePromise) return chartCorePromise
  chartCorePromise = Promise.all([
    import('echarts/core'),
    import('echarts/charts'),
    import('echarts/components'),
    import('echarts/renderers'),
  ]).then(([core, charts, components, renderers]) => {
    core.use([
      charts.PieChart,
      charts.BarChart,
      charts.LineChart,
      components.TooltipComponent,
      components.LegendComponent,
      components.GridComponent,
      renderers.CanvasRenderer,
    ])
    initChart = core.init
  })
  return chartCorePromise
}

async function renderCharts() {
  await ensureChartCore()
  renderStatusChart()
  renderOutputChart()
  renderIncomeChart()
}

function renderStatusChart() {
  if (!statusChartRef.value || !initChart) return
  statusChart ||= initChart(statusChartRef.value)
  const colors = ['#9aa7b7', '#216af3', '#ff9718', '#21b879', '#7658ee']
  const data = work.project_status_distribution.map((item, index) => ({
    value: item.count,
    name: item.label,
    itemStyle: { color: colors[index] },
  }))
  const total = data.reduce((sum, item) => sum + Number(item.value), 0)
  statusChart.setOption({
    tooltip: { trigger: 'item' },
    legend: {
      right: 8,
      top: 18,
      orient: 'vertical',
      itemWidth: 10,
      itemHeight: 10,
      formatter(name: string) {
        const item = data.find(row => row.name === name)
        const rate = total ? ((Number(item?.value || 0) / total) * 100).toFixed(1) : '0.0'
        return `${name}        ${item?.value || 0} (${rate}%)`
      },
    },
    series: [{
      type: 'pie',
      radius: ['48%', '78%'],
      center: ['30%', '52%'],
      avoidLabelOverlap: true,
      label: {
        position: 'center',
        formatter: `总项目数\n{total|${total}}\n↑`,
        rich: { total: { fontSize: 24, fontWeight: 800, color: '#101828', lineHeight: 34 } },
        color: '#617085',
        lineHeight: 22,
      },
      labelLine: { show: false },
      data,
    }],
  })
}

function renderOutputChart() {
  if (!outputChartRef.value || !initChart) return
  outputChart ||= initChart(outputChartRef.value)
  const labels = annual.monthly_output.months.map(month => `${month}月`)
  outputChart.setOption({
    color: ['#78b7ff', '#91d8ad', '#1265e8', '#ff8d16'],
    tooltip: { trigger: 'axis' },
    legend: { top: 0, itemWidth: 14, itemHeight: 8 },
    grid: { top: 46, left: 48, right: 42, bottom: 32 },
    xAxis: { type: 'category', data: labels, axisTick: { show: false } },
    yAxis: [
      { type: 'value', name: '张数（张）', splitLine: { lineStyle: { color: '#edf1f6' } } },
      { type: 'value', name: '项目数（个）', splitLine: { show: false } },
    ],
    series: [
      { name: '白图最终图（张）', type: 'bar', stack: 'final', data: annual.monthly_output.white_final, barWidth: 18 },
      { name: '场景图最终图（张）', type: 'bar', stack: 'final', data: annual.monthly_output.scene_final, barWidth: 18 },
      { name: '最终图总数（张）', type: 'line', smooth: true, data: annual.monthly_output.final_total, symbolSize: 6 },
      { name: '完成项目数（个）', type: 'line', smooth: true, yAxisIndex: 1, data: annual.monthly_output.completed_projects, symbolSize: 6 },
    ],
  })
}

function renderIncomeChart() {
  if (!incomeChartRef.value || !initChart) return
  incomeChart ||= initChart(incomeChartRef.value)
  const labels = annual.monthly_income.months.map(month => `${month}月`)
  incomeChart.setOption({
    color: ['#1265e8', '#19a974', '#ff4b2c'],
    tooltip: { trigger: 'axis', valueFormatter: (value: number) => `¥${formatNumber(value)}` },
    legend: { top: 0, itemWidth: 14, itemHeight: 8 },
    grid: { top: 46, left: 62, right: 22, bottom: 32 },
    xAxis: { type: 'category', data: labels, axisTick: { show: false } },
    yAxis: { type: 'value', name: '金额（元）', splitLine: { lineStyle: { color: '#edf1f6' } } },
    series: [
      { name: '应收金额（元）', type: 'line', smooth: true, data: annual.monthly_income.receivable, symbolSize: 6 },
      { name: '已收金额（元）', type: 'line', smooth: true, data: annual.monthly_income.received, symbolSize: 6 },
      { name: '未收金额（元）', type: 'line', smooth: true, data: annual.monthly_income.unreceived, symbolSize: 6 },
    ],
  })
}

function percent(done: number, total: number) {
  if (!total) return 0
  return Math.round((done / total) * 1000) / 10
}

function formatNumber(value: number | string) {
  const number = Number(value || 0)
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: number % 1 === 0 ? 0 : 2 }).format(number)
}

function formatDate(value: string | null) {
  if (!value) return '--'
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

onMounted(async () => {
  await fetchCompass()
  resizeObserver = new ResizeObserver(() => {
    statusChart?.resize()
    outputChart?.resize()
    incomeChart?.resize()
  })
  ;[statusChartRef.value, outputChartRef.value, incomeChartRef.value].forEach(el => {
    if (el) resizeObserver?.observe(el)
  })
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  statusChart?.dispose()
  outputChart?.dispose()
  incomeChart?.dispose()
})
</script>

<style scoped>
.compass-page {
  min-height: 100%;
  padding: 16px 18px 24px;
  color: #111827;
  background: linear-gradient(180deg, #f7fbff 0%, #f4f8fc 100%);
}

.compass-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
}

.title-group {
  display: flex;
  align-items: baseline;
  gap: 18px;
}

.title-group h1 {
  margin: 0;
  font-size: 28px;
  line-height: 36px;
  font-weight: 900;
  color: #0f172a;
}

.title-group span {
  color: #98a2b3;
  font-weight: 600;
}

.filters {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-select {
  --el-border-radius-base: 6px;
}

.filter-select.year { width: 126px; }
.filter-select.month { width: 126px; }
.filter-select.client { width: 176px; }
.filter-select.shooting { width: 230px; }

.refresh-button {
  height: 40px;
  min-width: 92px;
  border: 0;
  color: #fff;
  background: #0f2438;
  border-radius: 6px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.metric-card {
  height: 132px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 22px;
  background: #fff;
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  box-shadow: 0 8px 20px rgba(16, 24, 40, 0.06);
}

.metric-icon {
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  border: 4px solid currentColor;
  color: #1769e8;
  background: #f5f9ff;
}

.metric-icon .el-icon { font-size: 31px; }
.metric-icon.green { color: #16a465; background: #f3fbf7; }
.metric-icon.orange { color: #ff4b2c; background: #fff6f2; }

.metric-copy { min-width: 0; }
.metric-label { color: #4f5f74; font-size: 15px; font-weight: 700; }
.metric-value { margin-top: 8px; color: #111827; font-size: 31px; line-height: 34px; font-weight: 900; }
.metric-value.blue { color: #0f172a; }
.metric-value.green { color: #16a465; }
.metric-value.orange { color: #ff4b2c; }
.metric-value small { margin-left: 5px; font-size: 13px; color: #667085; font-weight: 600; }
.metric-rate { margin-top: 12px; color: #768399; font-size: 13px; }
.metric-rate span { margin-left: 8px; font-weight: 800; }
.metric-rate .up { color: #1769e8; }
.metric-rate .down { color: #ff4b2c; }

.panel {
  margin-bottom: 12px;
  background: #fff;
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  box-shadow: 0 8px 20px rgba(16, 24, 40, 0.04);
  overflow: hidden;
}

.section-header {
  height: 38px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  font-size: 18px;
  font-weight: 900;
  border-bottom: 1px solid #d7e0ea;
}

.work-grid {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr 1.1fr;
}

.trend-grid,
.client-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.client-grid {
  grid-template-columns: 1fr 1fr 1fr;
}

.sub-panel {
  min-width: 0;
  padding: 14px 16px;
  border-right: 1px solid #d7e0ea;
}

.sub-panel:last-child { border-right: 0; }
.sub-panel h3 {
  margin: 0 0 10px;
  font-size: 15px;
  color: #1d2939;
  font-weight: 900;
}

.sub-panel h3 span {
  font-size: 13px;
  color: #667085;
  font-weight: 600;
}

.chart { width: 100%; }
.status-chart { height: 216px; }
.trend-chart { height: 244px; }

.progress-panel {
  display: flex;
  flex-direction: column;
  gap: 26px;
}

.progress-item {
  padding: 8px 8px 0;
}

.progress-title {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 2px 16px;
  align-items: end;
  margin-bottom: 8px;
}

.progress-title span { color: #475467; font-size: 14px; font-weight: 700; }
.progress-title b { font-size: 25px; color: #111827; }
.progress-title b em { color: #0f69e8; font-style: normal; }
.progress-title small { grid-column: 2; color: #667085; }

.progress-scale {
  display: flex;
  justify-content: space-between;
  color: #8b96a8;
  font-size: 12px;
  margin-top: 4px;
}

.stage-panel {
  display: flex;
  flex-direction: column;
}

.stage-row {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1px 1fr 1px 1fr;
  align-items: center;
}

.stage-divider {
  height: 116px;
  background: #e3e8ef;
}

.stage-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 11px;
}

.stage-icon {
  width: 68px;
  height: 68px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #eaf3ff;
  color: #1769e8;
}

.stage-icon .el-icon { font-size: 38px; }
.stage-item.green .stage-icon { background: #dff7ec; color: #19a974; }
.stage-item.purple .stage-icon { background: #f0eaff; color: #7658ee; }
.stage-item span { color: #667085; font-weight: 700; }
.stage-item b { color: #0f172a; font-size: 30px; line-height: 32px; font-weight: 900; }
.stage-item small { margin-left: 4px; font-size: 12px; color: #667085; font-weight: 600; }

.trend-sub {
  padding-bottom: 4px;
}

.table-panel table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.table-panel th,
.table-panel td {
  height: 34px;
  padding: 0 10px;
  text-align: right;
  border-bottom: 1px solid #edf1f6;
  color: #435068;
  font-size: 13px;
}

.table-panel th:first-child,
.table-panel td:first-child {
  text-align: left;
}

.table-panel th {
  color: #667085;
  background: #f7f9fc;
  font-weight: 800;
}

.table-panel .danger {
  color: #ff4b2c;
}

.table-more {
  height: 32px;
  display: grid;
  place-items: center;
  color: #8a96a8;
  font-size: 12px;
}

.tab-active {
  color: #1769e8 !important;
  border-bottom: 2px solid #1769e8;
  padding-bottom: 4px;
}

.tab-muted {
  margin-left: 22px;
  color: #475467 !important;
}

.alert-panel h3 {
  display: flex;
  justify-content: space-between;
}

.alert-panel h3 span {
  color: #8a96a8;
  font-size: 12px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  border: 1px solid #e3e8ef;
  border-radius: 6px;
  overflow: hidden;
}

.alert-item {
  min-height: 54px;
  display: grid;
  grid-template-columns: 34px 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-bottom: 1px solid #edf1f6;
}

.alert-item:last-child { border-bottom: 0; }

.alert-icon {
  width: 26px;
  height: 26px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #ff4b2c;
  font-weight: 900;
}

.alert-body {
  min-width: 0;
}

.alert-body b {
  display: block;
  color: #1d2939;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.alert-body p {
  margin: 3px 0 0;
  color: #667085;
  font-size: 12px;
}

.alert-item time {
  color: #667085;
  font-size: 12px;
}

.empty,
.empty-alert {
  height: 92px;
  color: #98a2b3;
  text-align: center !important;
}

.empty-alert {
  display: grid;
  place-items: center;
}

:deep(.el-progress-bar__outer) {
  height: 10px !important;
  background: #dfe5ed;
}

:deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, #1769e8, #216af3);
}

@media (max-width: 1280px) {
  .compass-header {
    height: auto;
    align-items: flex-start;
    flex-direction: column;
  }
  .filters {
    flex-wrap: wrap;
  }
  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .work-grid,
  .trend-grid,
  .client-grid {
    grid-template-columns: 1fr;
  }
  .sub-panel {
    border-right: 0;
    border-bottom: 1px solid #d7e0ea;
  }
  .sub-panel:last-child {
    border-bottom: 0;
  }
}
</style>
