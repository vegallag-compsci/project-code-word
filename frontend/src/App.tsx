import { useCallback, useEffect, useRef, useState } from 'react'

type Status = 'connecting' | 'monitoring' | 'triggered' | 'saved' | 'error'

interface SavedEvent {
  type: 'saved'
  filename: string
}
interface ErrorEvent {
  type: 'error'
  message: string
}

const WS_URL = 'ws://127.0.0.1:8765/ws'

export default function App() {
  const imgRef = useRef<HTMLImageElement>(null)
  const prevUrlRef = useRef<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [status, setStatus] = useState<Status>('connecting')
  const [savedName, setSavedName] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const resetToMonitoring = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      setStatus('monitoring')
      setSavedName(null)
      setErrorMsg(null)
    }, 4000)
  }, [])

  useEffect(() => {
    const ws = new WebSocket(WS_URL)

    ws.binaryType = 'blob'

    ws.onopen = () => setStatus('monitoring')
    ws.onclose = () => setStatus('connecting')

    ws.onmessage = (e: MessageEvent) => {
      if (e.data instanceof Blob) {
        const url = URL.createObjectURL(e.data)
        if (imgRef.current) imgRef.current.src = url
        if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current)
        prevUrlRef.current = url
        return
      }

      try {
        const event = JSON.parse(e.data as string)
        if (event.type === 'gesture_detected') {
          setStatus('triggered')
          resetToMonitoring()
        } else if (event.type === 'saved') {
          setSavedName((event as SavedEvent).filename)
          setStatus('saved')
          resetToMonitoring()
        } else if (event.type === 'error') {
          setErrorMsg((event as ErrorEvent).message)
          setStatus('error')
          resetToMonitoring()
        }
      } catch {
        // ignore malformed messages
      }
    }

    return () => {
      ws.close()
      if (prevUrlRef.current) URL.revokeObjectURL(prevUrlRef.current)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [resetToMonitoring])

  const pill = statusPill(status, savedName, errorMsg)

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span
            className={`brand-dot ${status === 'monitoring' ? 'brand-dot--live' : ''}`}
            style={{ background: pill.color }}
          />
          <span className="brand-name">code_word</span>
        </div>

        <div className="status-pill" style={{ color: pill.color, borderColor: pill.color }}>
          {status === 'monitoring' && <span className="pulse" style={{ background: pill.color }} />}
          <span>{pill.label}</span>
          {status === 'saved' && savedName && (
            <span className="status-pill__file">{savedName}</span>
          )}
        </div>
      </header>

      <main className="main">
        <div className={`feed-card ${status === 'triggered' ? 'feed-card--flash' : ''}`}>
          <img
            ref={imgRef}
            className="feed-img"
            alt="Live camera feed"
            draggable={false}
          />
          {status === 'connecting' && (
            <div className="feed-overlay">
              <div className="spinner" />
              <p>Connecting to camera…</p>
            </div>
          )}
          {status === 'triggered' && (
            <div className="feed-overlay feed-overlay--triggered">
              <p className="triggered-label">Signal captured</p>
            </div>
          )}
        </div>
      </main>

      <footer className="footer">
        Hold up an open palm · last 20 s will be saved
      </footer>
    </div>
  )
}

function statusPill(
  status: Status,
  savedName: string | null,
  errorMsg: string | null
): { label: string; color: string } {
  switch (status) {
    case 'connecting':
      return { label: 'Connecting…', color: '#9CA3AF' }
    case 'monitoring':
      return { label: 'Monitoring', color: '#22C55E' }
    case 'triggered':
      return { label: 'Signal detected', color: '#F59E0B' }
    case 'saved':
      return { label: 'Saved', color: '#3B82F6' }
    case 'error':
      return { label: errorMsg ?? 'Error', color: '#EF4444' }
  }
}
