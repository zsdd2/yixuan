/**
 * 统一 HTTP 客户端
 * 封装原生 fetch API，提供请求/响应拦截器
 */

interface RequestOptions {
  method?: string
  headers?: Record<string, string>
  body?: any
  params?: Record<string, any>
}

class HttpClient {
  private baseURL: string = ''

  /**
   * 通用请求方法
   */
  private async request<T = any>(url: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', headers = {}, body, params } = options

    // 构建完整 URL
    let fullURL = this.baseURL + url
    if (params) {
      const queryString = new URLSearchParams(params).toString()
      fullURL += `?${queryString}`
    }

    // 请求拦截器：自动添加 Token
    const token = localStorage.getItem('token')
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    }

    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`
    }

    // 构建请求配置
    const config: RequestInit = {
      method,
      headers: requestHeaders,
    }

    if (body) {
      if (body instanceof FormData) {
        // FormData 自动设置 Content-Type
        delete requestHeaders['Content-Type']
        config.body = body
      } else {
        config.body = JSON.stringify(body)
      }
    }

    try {
      const response = await fetch(fullURL, config)

      // 响应拦截器：处理 401 未授权
      if (response.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('userInfo')
        window.location.href = '/login'
        throw new Error('登录已过期，请重新登录')
      }

      // 响应拦截器：处理 422 验证错误
      if (response.status === 422) {
        const errorData = await response.json().catch(() => ({ detail: '请求参数验证失败' }))
        throw new Error(errorData.detail || '请求参数验证失败')
      }

      // 响应拦截器：处理其他错误状态码
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `请求失败 (${response.status})` }))
        throw new Error(errorData.detail || `请求失败 (${response.status})`)
      }

      // 解析响应体
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      }

      return response as any
    } catch (error: any) {
      // 网络错误或其他异常
      if (error.message === '登录已过期，请重新登录') {
        throw error
      }
      throw new Error(error.message || '网络请求失败')
    }
  }

  /**
   * GET 请求
   */
  get<T = any>(url: string, params?: Record<string, any>, options: Omit<RequestOptions, 'method' | 'params'> = {}): Promise<T> {
    return this.request<T>(url, { ...options, method: 'GET', params })
  }

  /**
   * POST 请求
   */
  post<T = any>(url: string, body?: any, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return this.request<T>(url, { ...options, method: 'POST', body })
  }

  /**
   * PUT 请求
   */
  put<T = any>(url: string, body?: any, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return this.request<T>(url, { ...options, method: 'PUT', body })
  }

  /**
   * PATCH 请求
   */
  patch<T = any>(url: string, body?: any, options: Omit<RequestOptions, 'method' | 'body'> = {}): Promise<T> {
    return this.request<T>(url, { ...options, method: 'PATCH', body })
  }

  /**
   * DELETE 请求
   */
  delete<T = any>(url: string): Promise<T> {
    return this.request<T>(url, { method: 'DELETE' })
  }

  /**
   * 上传文件（FormData）
   */
  upload<T = any>(url: string, formData: FormData): Promise<T> {
    return this.request<T>(url, { method: 'POST', body: formData })
  }
}

const request = new HttpClient()

export default request
