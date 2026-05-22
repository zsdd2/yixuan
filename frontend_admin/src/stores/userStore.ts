/**
 * 用户状态管理 Store
 * 管理用户认证状态、Token、用户信息
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/api/request'

export type UserRole = 'super_admin' | 'admin' | 'staff' | 'client'

export interface UserInfo {
  user_id: number
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
}

interface LoginResponse {
  access_token: string
  token_type: string
  user_id: number
  username: string
  display_name: string
  role: UserRole
}

interface UserInfoResponse {
  user_id: number
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
}

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref<string | null>(null)
  const userInfo = ref<UserInfo | null>(null)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!userInfo.value)
  const isAdmin = computed(() => {
    const role = userInfo.value?.role
    return role === 'super_admin' || role === 'admin'
  })
  const isSuperAdmin = computed(() => userInfo.value?.role === 'super_admin')

  // 初始化：从 localStorage 恢复状态
  const initStore = () => {
    const savedToken = localStorage.getItem('token')
    const savedUserInfo = localStorage.getItem('userInfo')

    if (savedToken) {
      token.value = savedToken
    }

    if (savedUserInfo) {
      try {
        userInfo.value = JSON.parse(savedUserInfo)
      } catch (error) {
        console.error('Failed to parse userInfo from localStorage:', error)
        localStorage.removeItem('userInfo')
      }
    }
  }

  // 登录
  const login = async (username: string, password: string) => {
    try {
      const response = await request.post<LoginResponse>('/api/v1/auth/login', {
        username,
        password,
      })

      // 存储 Token 和用户信息
      token.value = response.access_token
      userInfo.value = {
        user_id: response.user_id,
        username: response.username,
        display_name: response.display_name,
        role: response.role,
        is_active: true,
      }

      // 持久化到 localStorage
      localStorage.setItem('token', response.access_token)
      localStorage.setItem('userInfo', JSON.stringify(userInfo.value))

      return response
    } catch (error: any) {
      throw new Error(error.message || '登录失败')
    }
  }

  // 登出
  const logout = () => {
    token.value = null
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    window.location.href = '/login'
  }

  // 获取当前用户信息
  const fetchUserInfo = async () => {
    try {
      const response = await request.get<UserInfoResponse>('/api/v1/auth/me')

      userInfo.value = {
        user_id: response.user_id,
        username: response.username,
        display_name: response.display_name,
        role: response.role,
        is_active: response.is_active,
      }

      // 更新 localStorage
      localStorage.setItem('userInfo', JSON.stringify(userInfo.value))

      return response
    } catch (error: any) {
      throw new Error(error.message || '获取用户信息失败')
    }
  }

  // 修改密码
  const updatePassword = async (oldPassword: string, newPassword: string) => {
    try {
      await request.put('/api/v1/auth/me/password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
    } catch (error: any) {
      throw new Error(error.message || '密码修改失败')
    }
  }

  // 初始化 Store
  initStore()

  return {
    // 状态
    token,
    userInfo,
    // 计算属性
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    // 方法
    login,
    logout,
    fetchUserInfo,
    updatePassword,
  }
})
