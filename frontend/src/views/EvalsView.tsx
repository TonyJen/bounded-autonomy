import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useGatewayWS, GatewayMessage } from '../lib/ws'
import StatCard from '../components/StatCard'

type CaseResult = { case_id: string; passed: boolean; score: number }

export default function EvalsView() {
  const [running, setRunning] = useState<string | null>(null)
  const [results, setResults] = useState<CaseResult[] | null>(null)
  const [summary, setSummary] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])

  const refreshHistory = useCallback(() => {
    api.getEvalHistory().then((h) => setHistory(h.runs)).catch(() => {})
  }, [])
  useEffect(refreshHistory, [refreshHistory])

  const poll = useCallback((jobId: string) => {
    const check = async () => {
      try {
        const job = await api.getEvalRun(jobId)
        if (job.status !== 'running') {
          clearInterval(timer)
          setRunning(null)
          if (job.status === 'completed') {
            setResults(job.result.results)
            setSummary(job.result.summary)
            refreshHistory()
          }
        }
      } catch { clearInterval(timer); setRunning(null) }
    }
    const timer = setInterval(check, 1000)
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
    try {
      const { run_id } = await api.runEvals(mode)
      poll(run_id)
    } catch { setRunning(null) }
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
          </span>
        )}
      </div>

      {results && (
        <StatCard title="Latest run">
          {results.map((r) => (
            <div key={r.case_id}
                 className="flex items-center gap-3 py-2 border-b
                            border-cardborder last:border-0">
              <span className={`text-sm px-2 py-0.5 rounded-full ${
                r.passed ? 'bg-good/20 text-good'
                         : 'bg-critical/20 text-critical'}`}>
                {r.passed ? '✓ pass' : '✗ fail'}
              </span>
              <span className="text-ink flex-1 font-mono text-sm">
                {r.case_id}
              </span>
              <div className="w-32 bg-cardborder rounded-full h-2">
                <div className="h-2 rounded-full bg-temp"
                     style={{ width: `${r.score * 100}%` }} />
              </div>
              <span className="text-ink2 text-sm w-12 text-right">
                {r.score.toFixed(2)}
              </span>
            </div>
          ))}
        </StatCard>
      )}

      <StatCard title="Run history">
        {history.length === 0 &&
          <div className="text-muted">No runs yet.</div>}
        {history.map((r) => (
          <div key={r.run_id}
               className="flex items-center gap-3 py-2 border-b
                          border-cardborder last:border-0 text-sm">
            <code className="text-muted">{r.run_id.slice(0, 15)}</code>
            <span className="text-ink2">{r.mode}</span>
            <span className="text-ink ml-auto">
              {r.summary.passed}/{r.summary.total}
            </span>
            <span className="text-muted">{r.summary.average_score}</span>
          </div>
        ))}
      </StatCard>
    </div>
  )
}
