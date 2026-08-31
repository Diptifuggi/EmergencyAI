// @ts-nocheck
import axios, { AxiosInstance } from 'axios'
import { API_BASE_URL } from '@/lib/constants'

const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
})

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    // You can enhance error handling here (logging, toasts)
    return Promise.reject(error)
  }
)

export default axiosInstance
