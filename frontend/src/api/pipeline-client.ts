/** 跨模块流水线 API 客户端：批次追溯、工序推进、门禁检查。 */
import { fetchJson, request } from './client'

const API = '/api/pipeline'

export interface TraceNode {
  module: string
  entry_id: number
  data: Record<string, string | number>
}

export interface TraceChain {
  batch_no: string
  chain: TraceNode[]
  weight_chain: Record<string, any>[]
  chain_length: number
  complete: boolean
  frozen_count: number
}

export interface GateDetail {
  batch_no: string
  passed: boolean
  message: string
  testing_checks: { total: number; confirmed: number }
  certification_checks: { total: number; confirmed: number }
}

export interface WeightConservation {
  batch_no: string
  picking_weight: number
  final_weight: number
  total_loss_pct: number
  conservation_ok: boolean
}

export async function fetchTraceChain(batchNo: string): Promise<TraceChain> {
  return fetchJson<TraceChain>(`${API}/${batchNo}/trace`)
}

export async function advanceBatch(
  batchNo: string,
  currentModule: string,
  currentEntryId: number,
  requestId?: string
): Promise<{ ok: boolean; message: string; entry: Record<string, any> }> {
  const params = new URLSearchParams({
    current_module: currentModule,
    current_entry_id: String(currentEntryId),
  })
  if (requestId) params.set('request_id', requestId)
  return fetchJson(`${API}/${batchNo}/advance?${params.toString()}`)
}

export async function checkGate(batchNo: string): Promise<{ ok: boolean; detail: GateDetail }> {
  return fetchJson(`${API}/${batchNo}/gate`)
}

export async function checkWeightConservation(batchNo: string): Promise<{
  ok: boolean; detail: WeightConservation
}> {
  return fetchJson(`${API}/${batchNo}/weight-conservation`)
}

export async function recalcMoisture(
  batchNo: string,
  processModule: string
): Promise<{ ok: boolean; detail: Record<string, any> }> {
  return fetchJson(`${API}/${batchNo}/moisture-recalc?process_module=${processModule}`)
}

export async function freezeDownstream(
  batchNo: string,
  defectEntryId: number,
  reason: string
): Promise<{ ok: boolean; frozen_count: number; frozen_keys: string[] }> {
  const params = new URLSearchParams({
    defect_entry_id: String(defectEntryId),
    reason,
  })
  return fetchJson(`${API}/${batchNo}/freeze-downstream?${params.toString()}`)
}

export async function linkSample(
  sampleEntryId: number,
  processModule: string,
  processEntryId: number
): Promise<{ ok: boolean; message: string }> {
  const params = new URLSearchParams({
    process_module: processModule,
    process_entry_id: String(processEntryId),
  })
  const response = await request(
    `${API}/sample/${sampleEntryId}/link?${params.toString()}`,
    { method: 'POST' }
  )
  if (!response.ok) {
    throw new Error('SAMPLE_LINK_FAILED')
  }
  return response.json()
}

export async function updateAuditReview(
  auditEntryId: number,
  reviewConclusion: string
): Promise<{ ok: boolean; message: string }> {
  const response = await request(
    `${API}/audit/${auditEntryId}/review?review_conclusion=${encodeURIComponent(reviewConclusion)}`,
    { method: 'POST' }
  )
  if (!response.ok) {
    throw new Error('AUDIT_REVIEW_FAILED')
  }
  return response.json()
}