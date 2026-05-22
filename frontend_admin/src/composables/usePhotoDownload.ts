import { ElMessage } from 'element-plus'

export interface DownloadablePhoto {
  id: number
  display_id: number
  original_path: string
  original_filename: string | null
}

export function usePhotoDownload() {
  function downloadOriginal(photo: DownloadablePhoto) {
    // 1. 校验 original_path
    if (!photo.original_path) {
      ElMessage.warning('该照片没有原图路径')
      return
    }

    try {
      // 2. 构建下载 URL（使用 encodeURIComponent 防止特殊字符）
      const url = `/storage/${photo.original_path}`

      // 3. 创建临时 <a> 标签触发下载
      const a = document.createElement('a')
      a.href = url

      // 4. 文件名降级处理
      let filename = photo.original_filename
      if (!filename) {
        const ext = photo.original_path.split('.').pop() || 'jpg'
        filename = `photo_${String(photo.display_id).padStart(3, '0')}.${ext}`
      }
      a.download = filename

      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (error) {
      console.error('下载失败:', error)
      ElMessage.error('下载失败，请重试')
    }
  }

  return {
    downloadOriginal
  }
}
