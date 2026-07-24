import type { ReportData } from '@/contracts'
import { apiGet } from '@/services/http/client'
import { httpClient } from '@/services/http/client'

export function getReport(
  projectId: string,
  version?: number,
): Promise<ReportData> {
  const params: Record<string, unknown> = {}
  if (version != null) params.version = version
  return apiGet<ReportData>(`/projects/${projectId}/report`, params)
}

export async function downloadReport(
  projectId: string,
  format: 'markdown' | 'html' = 'markdown',
  version?: number,
): Promise<{ blob: Blob; filename: string }> {
  const params: Record<string, unknown> = { format }
  if (version != null) params.version = version

  const response = await httpClient.get(
    `/projects/${projectId}/report/download`,
    {
      params,
      responseType: 'blob',
    },
  )

  // 从 Content-Disposition 提取文件名
  const disposition = response.headers['content-disposition'] as string | undefined
  let filename = `asa-report-${projectId}.${format === 'html' ? 'html' : 'md'}`
  if (disposition) {
    const match = /filename="?([^";\n]+)"?/.exec(disposition)
    if (match?.[1]) filename = match[1]
  }

  return { blob: response.data as Blob, filename }
}
