import axios from 'axios'

const apiClient = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
})

// Request interceptor — attach auth token when available
apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token')
        if (token) config.headers.Authorization = `Bearer ${token}`
        return config
    },
    (err) => Promise.reject(err)
)

// Response interceptor — normalize errors
apiClient.interceptors.response.use(
    (res) => res,
    (err) => {
        const msg = err.response?.data?.detail || err.message || 'Unknown error'
        console.error('[API Error]', msg)
        return Promise.reject(new Error(msg))
    }
)

export default apiClient
