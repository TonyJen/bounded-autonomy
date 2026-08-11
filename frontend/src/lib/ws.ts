import { useEffect, useRef, useState } from 'react'

export type GatewayMessage = {
  type: 'snapshot' | 'actuator' | 'decision' | 'eval_progress'
  data: any
}

export function useGatewayWS(onMessage: (msg: GatewayMessage) => void) {
  const [connected, setConnected] = useState(false)
  const handlerRef = useRef(onMessage)
  handlerRef.current = onMessage

  useEffect(() => {
    let ws: WebSocket | null = null
    let closed = false
    let backoff = 1000

    const connect = () => {
      if (closed) return
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${window.location.host}/ws`)
      ws.onopen = () => { setConnected(true); backoff = 1000 }
      ws.onmessage = (ev) => {
        try { handlerRef.current(JSON.parse(ev.data)) } catch { /* ignore */ }
      }
      ws.onclose = () => {
        setConnected(false)
        if (!closed) setTimeout(connect, backoff)
        backoff = Math.min(backoff * 2, 10000)
      }
    }
    connect()
    return () => { closed = true; ws?.close() }
  }, [])

  return { connected }
}
