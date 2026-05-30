import { ElMessage } from 'element-plus'

export interface DownloadablePhoto {
  id: number
  display_id: number | string
  original_path: string
  original_filename: string | null
}

function fallbackName(path: string, displayId: number | string, prefix = 'photo') {
  const ext = path.split('.').pop() || 'jpg'
  return `${prefix}_${String(displayId).padStart(3, '0')}.${ext}`
}

export async function downloadStorageFile(path: string, filename?: string | null) {
  if (!path) {
    ElMessage.warning('文件路径为空')
    return
  }

  try {
    const token = localStorage.getItem('token')
    const params = new URLSearchParams({ path })
    if (filename) params.set('filename', filename)

    const res = await fetch(`/api/v1/system/download?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })

    if (!res.ok) {
      const detail = await res.text().catch(() => '')
      throw new Error(detail || `HTTP ${res.status}`)
    }

    const blob = await res.blob()
    if (blob.size === 0) throw new Error('下载文件为空')

    const objectUrl = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename || path.split('/').pop() || 'download'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(objectUrl)
  } catch (error: any) {
    console.error('下载失败:', error)
    ElMessage.error(error?.message || '下载失败，请重试')
  }
}

export function usePhotoDownload() {
  function downloadOriginal(photo: DownloadablePhoto | null | undefined) {
    if (!photo?.original_path) {
      ElMessage.warning('该照片没有原图路径')
      return
    }
    const filename = photo.original_filename || fallbackName(photo.original_path, photo.display_id)
    downloadStorageFile(photo.original_path, filename)
  }

  return {
    downloadOriginal,
  }
}
