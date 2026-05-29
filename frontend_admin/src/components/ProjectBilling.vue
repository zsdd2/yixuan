<template>
  <div class="billing-page">
    <div class="billing-topbar">
      <el-button text :icon="ArrowLeft" @click="$emit('back')">返回项目</el-button>
      <div class="topbar-title">
        <h2>账目明细</h2>
        <span>按项目最终成图计费，项目完成和收款完成分开判定</span>
      </div>
      <div v-if="isSuperAdmin && !accessDenied" class="topbar-actions">
        <el-button :loading="loading" @click="syncBilling">同步成片</el-button>
        <el-button type="primary" :disabled="summary.billing_status === 'paid'" @click="confirmBilling">确认账单</el-button>
        <el-button type="success" :disabled="summary.billing_status === 'paid'" @click="markPaid">确认收款</el-button>
      </div>
    </div>

    <el-empty v-if="accessDenied" description="账目未锁定，暂无查看权限" />

    <template v-else>
      <div class="summary-grid" v-loading="loading">
        <div class="summary-cell">
          <span class="label">成片计费</span>
          <b>{{ data.final_photo_count }} 张</b>
          <small>自动同步有效最终成图</small>
        </div>
        <div class="summary-cell">
          <span class="label">项目状态</span>
          <b>{{ summary.work_completed ? '已做完' : '未做完' }}</b>
          <small>{{ workStatusLabel[summary.work_status] || summary.work_status }}</small>
        </div>
        <div class="summary-cell">
          <span class="label">收款状态</span>
          <b>{{ summary.payment_completed ? '已收款' : billingStatusLabel[summary.billing_status] }}</b>
          <small>{{ summary.paid_at ? formatDate(summary.paid_at) : '未确认收款' }}</small>
        </div>
        <div class="summary-cell total">
          <span class="label">应收合计</span>
          <b>¥{{ money(summary.total_amount) }}</b>
          <small>成片 ¥{{ money(summary.subtotal_amount) }} / 调整 ¥{{ money(summary.adjustment_amount) }}</small>
        </div>
      </div>

      <div class="billing-section">
        <div class="section-title">
          <h3>最终成图计费</h3>
          <span>制作类型从客户计费规则带出价格，可按单张手动改价</span>
        </div>
        <el-table :data="autoItems" border stripe empty-text="暂无最终成图计费">
          <el-table-column label="图片" width="92" align="center">
            <template #default="{ row }">
              <el-image v-if="row.thumbnail_path" :src="storageUrl(row.thumbnail_path)" fit="cover" class="thumb" lazy />
              <div v-else class="thumb empty">#{{ row.display_id || '-' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="编号" width="80">
            <template #default="{ row }">#{{ row.display_id || '-' }}</template>
          </el-table-column>
          <el-table-column prop="target_name" label="子项目" min-width="140" show-overflow-tooltip />
          <el-table-column label="基础分类" width="100">
            <template #default="{ row }">{{ categoryLabel(row.base_category_type) }}</template>
          </el-table-column>
          <el-table-column label="制作类型" width="170">
            <template #default="{ row }">
              <el-select
                v-model="row.production_type"
                size="small"
                :disabled="readonly"
                @change="onProductionChange(row)"
              >
                <el-option
                  v-for="rule in rulesFor(row)"
                  :key="`${rule.base_category_type}-${rule.production_type}`"
                  :label="rule.production_name"
                  :value="rule.production_type"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="单价" width="130">
            <template #default="{ row }">
              <el-input-number v-model="row.unit_price" :disabled="readonly" :min="0" :precision="2" :step="10" size="small" controls-position="right" />
            </template>
          </el-table-column>
          <el-table-column label="数量" width="110">
            <template #default="{ row }">
              <el-input-number v-model="row.quantity" :disabled="readonly" :min="0.01" :precision="2" :step="1" size="small" controls-position="right" />
            </template>
          </el-table-column>
          <el-table-column label="计费" width="90" align="center">
            <template #default="{ row }">
              <el-switch v-model="row.is_excluded" :disabled="readonly" :active-value="false" :inactive-value="true" />
            </template>
          </el-table-column>
          <el-table-column label="小计" width="110" align="right">
            <template #default="{ row }">¥{{ money(row.is_excluded ? 0 : row.quantity * row.unit_price) }}</template>
          </el-table-column>
          <el-table-column label="备注" min-width="160">
            <template #default="{ row }">
              <el-input v-model="row.notes" :disabled="readonly" size="small" placeholder="可为空" />
            </template>
          </el-table-column>
          <el-table-column v-if="!readonly" label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link @click="saveItem(row)">保存</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="billing-section">
        <div class="section-title">
          <h3>手动费用</h3>
          <el-button v-if="!readonly" size="small" type="primary" @click="showManualDialog = true">新增费用</el-button>
        </div>
        <el-table :data="manualItems" border stripe empty-text="暂无手动费用">
          <el-table-column prop="production_name" label="费用类型" min-width="140" />
          <el-table-column prop="notes" label="说明" min-width="180" show-overflow-tooltip />
          <el-table-column label="数量" width="100">
            <template #default="{ row }">{{ row.quantity }}</template>
          </el-table-column>
          <el-table-column label="单价" width="120" align="right">
            <template #default="{ row }">¥{{ money(row.unit_price) }}</template>
          </el-table-column>
          <el-table-column label="小计" width="120" align="right">
            <template #default="{ row }">¥{{ money(row.amount) }}</template>
          </el-table-column>
          <el-table-column v-if="!readonly" label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" link @click="deleteItem(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </template>

    <el-dialog v-model="showManualDialog" title="新增手动费用" width="460px">
      <el-form :model="manualForm" label-width="90px">
        <el-form-item label="费用类型">
          <el-input v-model="manualForm.production_name" placeholder="如加急费、额外修图费、折扣" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="manualForm.quantity" :min="0.01" :precision="2" :step="1" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="manualForm.unit_price" :min="-999999" :precision="2" :step="10" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="manualForm.notes" type="textarea" :rows="3" placeholder="可为空" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showManualDialog = false">取消</el-button>
        <el-button type="primary" @click="createManualItem">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'
import { useUserStore } from '../stores/userStore'

const props = defineProps<{ projectId: number }>()
defineEmits<{ (e: 'back'): void }>()

interface BillingSummary {
  project_id: number
  subtotal_amount: number
  adjustment_amount: number
  total_amount: number
  billing_status: string
  confirmed_at: string | null
  paid_at: string | null
  work_status: string
  work_completed: boolean
  payment_completed: boolean
}

interface BillingRule {
  id: number
  base_category_type: string
  production_type: string
  production_name: string
  unit_price: number
  is_default: boolean
  is_active: boolean
}

interface BillingItem {
  id: number
  photo_id: number | null
  target_name: string | null
  display_id: number | null
  thumbnail_path: string | null
  base_category_type: string
  production_type: string
  production_name: string
  quantity: number
  unit_price: number
  amount: number
  source: string
  notes: string | null
  is_excluded: boolean
}

const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const readonly = computed(() => !isSuperAdmin.value || summary.billing_status === 'paid')

const loading = ref(false)
const accessDenied = ref(false)
const showManualDialog = ref(false)
const data = reactive({
  items: [] as BillingItem[],
  price_rules: [] as BillingRule[],
  final_photo_count: 0,
})
const summary = reactive<BillingSummary>({
  project_id: props.projectId,
  subtotal_amount: 0,
  adjustment_amount: 0,
  total_amount: 0,
  billing_status: 'draft',
  confirmed_at: null,
  paid_at: null,
  work_status: 'not_started',
  work_completed: false,
  payment_completed: false,
})
const manualForm = reactive({
  production_name: '',
  quantity: 1,
  unit_price: 0,
  notes: '',
})

const billingStatusLabel: Record<string, string> = {
  draft: '草稿',
  confirmed: '已确认',
  paid: '已收款',
}
const workStatusLabel: Record<string, string> = {
  not_started: '未开始',
  shooting: '拍摄中',
  retouching: '修图中',
  client_review: '客户审核',
  completed: '已完成',
}

const autoItems = computed(() => data.items.filter(item => item.source === 'auto'))
const manualItems = computed(() => data.items.filter(item => item.source === 'manual'))

function applyResponse(res: any) {
  accessDenied.value = false
  Object.assign(summary, res.summary)
  data.items = res.items || []
  data.price_rules = res.price_rules || []
  data.final_photo_count = res.final_photo_count || 0
}

async function fetchBilling() {
  loading.value = true
  try {
    applyResponse(await request.get(`/api/v1/projects/${props.projectId}/billing`))
  } catch (e: any) {
    if ((e.message || '').includes('账目未锁定')) {
      accessDenied.value = true
    } else {
      ElMessage.error(e.message || '获取账目失败')
    }
  } finally {
    loading.value = false
  }
}

async function syncBilling() {
  loading.value = true
  try {
    applyResponse(await request.post(`/api/v1/projects/${props.projectId}/billing/sync`, {}))
    ElMessage.success('已同步最终成图')
  } catch (e: any) {
    ElMessage.error(e.message || '同步失败')
  } finally {
    loading.value = false
  }
}

function categoryLabel(type: string) {
  return type === 'white' ? '白图' : type === 'scene' ? '场景图' : '其他'
}

function rulesFor(row: BillingItem) {
  const rules = data.price_rules.filter(rule =>
    rule.base_category_type === row.base_category_type &&
    (rule.is_active || rule.production_type === row.production_type)
  )
  if (rules.some(rule => rule.production_type === row.production_type)) return rules
  return [
    ...rules,
    {
      id: 0,
      base_category_type: row.base_category_type,
      production_type: row.production_type,
      production_name: row.production_name,
      unit_price: row.unit_price,
      is_default: false,
      is_active: true,
    },
  ]
}

function onProductionChange(row: BillingItem) {
  const rule = data.price_rules.find(item =>
    item.base_category_type === row.base_category_type &&
    item.production_type === row.production_type
  )
  if (!rule) return
  row.production_name = rule.production_name
  row.unit_price = rule.unit_price
}

async function saveItem(row: BillingItem) {
  try {
    applyResponse(await request.patch(`/api/v1/projects/${props.projectId}/billing/items/${row.id}`, {
      base_category_type: row.base_category_type,
      production_type: row.production_type,
      production_name: row.production_name,
      quantity: row.quantity,
      unit_price: row.unit_price,
      notes: row.notes,
      is_excluded: row.is_excluded,
    }))
    ElMessage.success('已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  }
}

async function createManualItem() {
  if (!manualForm.production_name.trim()) {
    ElMessage.warning('请输入费用类型')
    return
  }
  try {
    applyResponse(await request.post(`/api/v1/projects/${props.projectId}/billing/items`, {
      base_category_type: 'manual',
      production_type: 'manual',
      production_name: manualForm.production_name.trim(),
      quantity: manualForm.quantity,
      unit_price: manualForm.unit_price,
      notes: manualForm.notes || null,
    }))
    Object.assign(manualForm, { production_name: '', quantity: 1, unit_price: 0, notes: '' })
    showManualDialog.value = false
    ElMessage.success('费用已添加')
  } catch (e: any) {
    ElMessage.error(e.message || '新增失败')
  }
}

async function deleteItem(row: BillingItem) {
  try {
    await ElMessageBox.confirm('确定删除这条费用吗？', '删除确认', { type: 'warning' })
    applyResponse(await request.delete(`/api/v1/projects/${props.projectId}/billing/items/${row.id}`))
    ElMessage.success('已删除')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '删除失败')
  }
}

async function confirmBilling() {
  try {
    applyResponse(await request.post(`/api/v1/projects/${props.projectId}/billing/confirm`, {}))
    ElMessage.success('账单已确认')
  } catch (e: any) {
    ElMessage.error(e.message || '确认失败')
  }
}

async function markPaid() {
  try {
    await ElMessageBox.confirm('确认该项目款项已经收完？', '确认收款', { type: 'warning' })
    applyResponse(await request.post(`/api/v1/projects/${props.projectId}/billing/mark-paid`, {}))
    ElMessage.success('已确认收款')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e.message || '确认收款失败')
  }
}

function storageUrl(path: string): string {
  return `/storage/${path}`
}

function money(value: number): string {
  return Number(value || 0).toFixed(2)
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

onMounted(fetchBilling)
</script>

<style scoped>
.billing-page { padding: 24px; min-height: 100%; background: #f5f7fb; }
.billing-topbar { display: flex; align-items: center; gap: 18px; margin-bottom: 18px; }
.topbar-title { flex: 1; }
.topbar-title h2 { margin: 0 0 4px; font-size: 22px; color: #1f2d3d; }
.topbar-title span { color: #6b7280; font-size: 13px; }
.topbar-actions { display: flex; gap: 8px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }
.summary-cell { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 6px; }
.summary-cell .label { font-size: 13px; color: #6b7280; }
.summary-cell b { font-size: 24px; color: #111827; }
.summary-cell small { color: #8a94a6; }
.summary-cell.total b { color: #1677ff; }
.billing-section { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.section-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-title h3 { margin: 0; font-size: 16px; color: #1f2d3d; }
.section-title span { color: #8a94a6; font-size: 13px; }
.thumb { width: 58px; height: 58px; border-radius: 6px; background: #f3f4f6; }
.thumb.empty { display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 12px; }
@media (max-width: 1100px) {
  .billing-topbar { flex-wrap: wrap; }
  .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
