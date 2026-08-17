import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useGatewayWS, GatewayMessage } from '../lib/ws'
import StatCard from '../components/StatCard'

type CaseResult = {
  case_id: string
  passed: boolean
  score: number
  detail?: {
    required_ok?: boolean
    forbidden_ok?: boolean
    args_ok?: boolean
    called?: string[]
    custom_check_failed?: string
  }
  perf?: { latency_ms: number; input_tokens: number; output_tokens: number }
}

export default function EvalsView() {
  const [running, setRunning] = useState<string | null>(null)
  const [results, setResults] = useState<CaseResult[] | null>(null)
  const [summary, setSummary] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [viewingRun, setViewingRun] = useState<string | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null }
  }
  // no polling past unmount (tab switches must not leak intervals)
  useEffect(() => stopPolling, [])

  const refreshHistory = useCallback(() => {
    api.getEvalHistory().then((h) => setHistory(h.runs)).catch(() => {})
  }, [])
  useEffect(refreshHistory, [refreshHistory])

  const poll = useCallback((jobId: string) => {
    const check = async () => {
      try {
        const job = await api.getEvalRun(jobId)
        if (job.status !== 'running') {
          stopPolling()
          setRunning(null)
          if (job.status === 'completed') {
            setResults(job.result.results)
            setSummary({ ...job.result.summary,
                         mode: job.result.metadata?.mode })
            refreshHistory()
          } else {
            setRunError(job.error ?? 'eval run failed')
          }
        }
      } catch {
        stopPolling()
        setRunning(null)
        setRunError('lost contact with the gateway mid-run')
      }
    }
    stopPolling()
    pollTimer.current = setInterval(check, 1000)
    // Check immediately too — a fast mock run can finish before the first tick.
    check()
  }, [refreshHistory])

  const onMessage = useCallback((msg: GatewayMessage) => {
    if (msg.type === 'eval_progress' && msg.data.status !== 'running') {
      refreshHistory()
    }
  }, [refreshHistory])
  useGatewayWS(onMessage)

  const run = async (mode: 'mock' | 'live') => {
    setRunning(mode)
    setResults(null)
    setViewingRun(null)
    setRunError(null)
    try {
      const { run_id } = await api.runEvals(mode)
      poll(run_id)
    } catch {
      setRunning(null)
      setRunError(`could not start ${mode} run — is the gateway up?`)
    }
  }

  const openRun = async (runId: string, mode: string) => {
    try {
      const record = await api.getEvalRecord(runId)
      setResults(record.results)
      setSummary({ ...record.summary, mode })
      setViewingRun(runId)
    } catch { /* record missing for this run — leave current view */ }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <button onClick={() => run('mock')} disabled={!!running}
          className="px-4 py-2 rounded-md bg-temp/20 text-temp disabled:opacity-40">
          {running === 'mock' ? 'Running…' : 'Run mock'}
        </button>
        <button onClick={() => run('live')} disabled={!!running}
          className="px-4 py-2 rounded-md bg-warning/20 text-warning disabled:opacity-40">
          {running === 'live' ? 'Running…' : 'Run live (API tokens)'}
        </button>
        {summary && (
          <span className="text-ink ml-4">
            {summary.passed}/{summary.total} passed · avg {summary.average_score}
            {summary.avg_latency_ms != null && (
              <span className="text-muted">
                {' '}· {(summary.avg_latency_ms / 1000).toFixed(1)}s avg ·{' '}
                {(summary.total_input_tokens ?? 0).toLocaleString()}→
                {(summary.total_output_tokens ?? 0).toLocaleString()} tok
              </span>
            )}
          </span>
        )}
      </div>

      {runError && (
        <div className="px-3 py-2 rounded-md bg-critical/20 text-critical text-sm">
          ✗ {runError}
        </div>
      )}

      {results && (
        <StatCard title={viewingRun
          ? `Run ${viewingRun.slice(0, 15)}… (${summary?.mode ?? ''})`
          : 'Latest run'}>
          <div className="flex items-center gap-3 pb-2 text-xs text-muted">
            <span className="w-16" />
            <span className="flex-1">case</span>
            <span className="w-40 text-center">correctness</span>
            <span className="w-36 text-right">performance</span>
            <span className="w-36 text-right">score</span>
          </div>
          {results.map((r) => (
            <div key={r.case_id}
                 className="flex items-center gap-3 py-2 border-b
                            border-cardborder last:border-0">
              <span className={`text-sm px-2 py-0.5 rounded-full w-16 text-center ${
                r.passed ? 'bg-good/20 text-good'
                         : 'bg-critical/20 text-critical'}`}>
                {r.passed ? '✓ pass' : '✗ fail'}
              </span>
              <span className="text-ink flex-1 font-mono text-sm">
                {r.case_id}
              </span>
              <span className="w-40 flex justify-center gap-1">
                {(['required_ok', 'forbidden_ok', 'args_ok'] as const).map((k) => (
                  <span key={k} title={k}
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      r.detail?.[k] === false
                        ? 'bg-critical/20 text-critical'
                        : 'bg-good/20 text-good'}`}>
                    {k === 'required_ok' ? 'req' : k === 'forbidden_ok' ? 'forb' : 'args'}
                    {r.detail?.[k] === false ? ' ✗' : ' ✓'}
                  </span>
                ))}
              </span>
              <span className="w-36 text-right text-ink2 text-xs">
                {r.perf
                  ? `${(r.perf.latency_ms / 1000).toFixed(1)}s · ${r.perf.input_tokens.toLocaleString()}→${r.perf.output_tokens.toLocaleString()} tok`
                  : '—'}
              </span>
              <span className="w-36 flex items-center justify-end gap-2">
                <div className="w-24 bg-cardborder rounded-full h-2">
                  <div className="h-2 rounded-full bg-temp"
                       style={{ width: `${r.score * 100}%` }} />
                </div>
                <span className="text-ink2 text-sm w-10 text-right">
                  {r.score.toFixed(2)}
                </span>
              </span>
            </div>
          ))}
          {results.some((r) => r.detail?.custom_check_failed) && (
            <div className="pt-2 text-xs text-critical">
              {results.find((r) => r.detail?.custom_check_failed)
                ?.detail?.custom_check_failed}
            </div>
          )}
        </StatCard>
      )}

      <StatCard title="Run history (click a run to drill down)">
        {history.length === 0 &&
          <div className="text-muted">No runs yet.</div>}
        {history.map((r) => (
          <button key={r.run_id}
               onClick={() => openRun(r.run_id, r.mode)}
               className={`w-full flex items-center gap-3 py-2 border-b
                          border-cardborder last:border-0 text-sm text-left
                          hover:bg-bg/60 rounded px-1 ${
                            viewingRun === r.run_id ? 'bg-bg' : ''}`}>
            <code className="text-muted">{r.run_id.slice(0, 15)}</code>
            <span className="text-ink2">{r.mode}</span>
            <span className="text-ink ml-auto">
              {r.summary.passed}/{r.summary.total}
            </span>
            {r.summary.avg_latency_ms != null && (
              <span className="text-muted">
                {(r.summary.avg_latency_ms / 1000).toFixed(1)}s
              </span>
            )}
            <span className="text-muted">{r.summary.average_score}</span>
          </button>
        ))}
      </StatCard>
    </div>
  )
}
