import { WS_CLOSE_CODES, type WsConnectionStatus, type WsEvent, type WsPing, type WsPong } from '@/contracts'

export type EventHandler = (event: WsEvent) => void
export type StatusHandler = (status: WsConnectionStatus) => void

interface WsOptions {
  projectId: string
  afterSequence?: number
  heartbeatIntervalMs?: number
  pongTimeoutMs?: number
  maxReconnectAttempts?: number
  initialBackoffMs?: number
  maxBackoffMs?: number
}

const DEFAULT_OPTIONS = {
  heartbeatIntervalMs: 15000,
  pongTimeoutMs: 10000,
  maxReconnectAttempts: 10,
  initialBackoffMs: 1000,
  maxBackoffMs: 30000,
} as const

export class WsConnection {
  private ws: WebSocket | null = null
  private options: Required<WsOptions>
  private eventHandler: EventHandler | null = null
  private statusHandler: StatusHandler | null = null
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private pongTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private intentionalClose = false
  private _status: WsConnectionStatus = 'disconnected'

  constructor(options: WsOptions) {
    this.options = { ...DEFAULT_OPTIONS, ...options, afterSequence: options.afterSequence ?? 0 }
  }

  get status(): WsConnectionStatus {
    return this._status
  }

  private setStatus(status: WsConnectionStatus): void {
    this._status = status
    this.statusHandler?.(status)
  }

  onEvent(handler: EventHandler): void {
    this.eventHandler = handler
  }

  onStatusChange(handler: StatusHandler): void {
    this.statusHandler = handler
  }

  connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.intentionalClose = false
    this.setStatus('connecting')

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/api/v1/projects/${this.options.projectId}/stream?after_sequence=${this.options.afterSequence}`

    try {
      this.ws = new WebSocket(url, 'asa.v1')
      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onclose = this.handleClose.bind(this)
      this.ws.onerror = this.handleError.bind(this)
    } catch {
      this.setStatus('disconnected')
      this.scheduleReconnect()
    }
  }

  disconnect(): void {
    this.intentionalClose = true
    this.clearTimers()
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
    this.setStatus('disconnected')
  }

  updateAfterSequence(sequence: number): void {
    this.options.afterSequence = sequence
  }

  private handleOpen(): void {
    this.reconnectAttempts = 0
    this.setStatus('connected')
    this.startHeartbeat()
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data as string)

      // 处理心跳响应
      if (data.type === 'pong') {
        this.handlePong(data as WsPong)
        return
      }

      // 处理业务事件
      if (data.event_id && data.sequence !== undefined) {
        this.eventHandler?.(data as WsEvent)
      }
    } catch {
      // 忽略无法解析的消息
    }
  }

  private handleClose(event: CloseEvent): void {
    this.clearTimers()

    if (this.intentionalClose) {
      this.setStatus('disconnected')
      return
    }

    const code = event.code

    switch (code) {
      case WS_CLOSE_CODES.SESSION_EXPIRED:
        // 会话过期 → 跳转登录
        this.setStatus('disconnected')
        import('@/stores/auth.store').then(({ useAuthStore }) => {
          useAuthStore().clearSession()
          import('@/router').then(({ router }) => router.push('/login'))
        })
        return

      case WS_CLOSE_CODES.PROJECT_ACCESS_DENIED:
        // 权限撤销 → 403
        this.setStatus('disconnected')
        import('@/router').then(({ router }) => router.push('/403'))
        return

      case WS_CLOSE_CODES.RATE_LIMITED:
        // 限流 → 等待后重连
        this.setStatus('reconnecting')
        this.scheduleReconnect(this.options.initialBackoffMs * 4)
        return

      case WS_CLOSE_CODES.EVENT_GAP_TOO_LARGE:
        // 事件缺口 → 全量补偿
        this.setStatus('compensating')
        // 由上层 composable 触发 REST 全量补偿
        return

      case WS_CLOSE_CODES.CLIENT_TOO_SLOW:
        // 客户端太慢 → 降低频率后重连
        this.setStatus('reconnecting')
        this.scheduleReconnect(this.options.initialBackoffMs * 2)
        return

      default:
        // 普通断线 → 重连
        this.setStatus('reconnecting')
        this.scheduleReconnect()
    }
  }

  private handleError(): void {
    // onerror 后通常会触发 onclose，这里只做标记
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        const ping: WsPing = {
          type: 'ping',
          sent_at: new Date().toISOString(),
        }
        this.ws.send(JSON.stringify(ping))

        // 设置 pong 超时
        this.pongTimer = setTimeout(() => {
          // pong 超时，认为连接断开
          this.ws?.close(1011, 'Pong timeout')
        }, this.options.pongTimeoutMs)
      }
    }, this.options.heartbeatIntervalMs)
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
    if (this.pongTimer) {
      clearTimeout(this.pongTimer)
      this.pongTimer = null
    }
  }

  private handlePong(_pong: WsPong): void {
    // 收到 pong，清除超时
    if (this.pongTimer) {
      clearTimeout(this.pongTimer)
      this.pongTimer = null
    }
  }

  private scheduleReconnect(delay?: number): void {
    if (this.intentionalClose) return
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      this.setStatus('disconnected')
      return
    }

    const backoff = delay ?? Math.min(
      this.options.initialBackoffMs * Math.pow(2, this.reconnectAttempts),
      this.options.maxBackoffMs,
    )
    // 添加随机抖动 ±10%
    const jitter = backoff * (0.9 + Math.random() * 0.2)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, jitter)
  }

  private clearTimers(): void {
    this.stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }
}
