import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { useGatewayWS, GatewayMessage } from '../lib/ws'
import { fmtTime } from '../lib/format'
import StatCard from '../components/StatCard'

type Decision = {
  id: number; ts: string; trigger: string; source: string
  context_json: string; tool_calls_json: string
  latency_ms: number | null; input_tokens: number | null
  output_tokens: number | null
}

function parseCalls(d: Decision): { name: string; args: any }[] {
  try { return JSON.parse(d.tool_calls_json) } catch { return [] }
}

/** context_json comes from SQLite and is shown raw in the UI; a malformed
 *  row must not crash the whole view during render. */
function parseContext(d: Decision): any {
  try { return JSON.parse(d.context_json || '{}') } catch { return {} }
}

export default function AgentView() {
  const [decisions, setDecisions] = useState<Decision[]>([])

  const onMessage = useCallback((_msg: GatewayMessage) => {
    if (_msg.type === 'decision') {
      api.getHistory(20).then((h) => setDecisions(h.decisions)).catch(() => {})
    }
  }, [])
  useGatewayWS(onMessage)

  useEffect(() => {
    api.getHistory(20).then((h) => setDecisions(h.decisions)).catch(() => {})
  }, [])

  const latest = decisions[0]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <StatCard title="Decision log" className="lg:col-span-2">
        <div className="space-y-3">
          {decisions.length === 0 && (
            <div className="text-muted">No decisions yet — waiting for a
              heartbeat or event…</div>)}
          {decisions.map((d) => (
            <div key={d.id} className="border-b border-cardborder pb-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted">{fmtTime(d.ts)}</span>
                <span className="text-ink2">{d.trigger}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs ${
                  d.source === 'agent'
                    ? 'bg-light/20 text-light'
                    : 'bg-warning/20 text-warning'}`}>
                  {d.source}
                </span>
                <span className="ml-auto text-muted text-xs">
                  {(d.input_tokens ?? 0).toLocaleString()}→
                  {(d.output_tokens ?? 0).toLocaleString()} tok
                  {d.latency_ms != null &&
                    ` · ${(d.latency_ms / 1000).toFixed(1)}s`}
                </span>
              </div>
              <div className="flex flex-wrap gap-1 mt-1">
                {parseCalls(d).map((c, i) => (
                  <code key={i}
                    className="text-xs bg-bg rounded px-2 py-0.5 text-ink">
                    {c.name}({JSON.stringify(c.args)})
                  </code>
                ))}
                {parseCalls(d).length === 0 &&
                  <span className="text-muted text-xs">no tool calls</span>}
              </div>
            </div>
          ))}
        </div>
      </StatCard>

      <StatCard title="Latest decision">
        {latest ? (
          <>
            <div className="text-4xl font-semibold text-ink mb-1">
              {parseCalls(latest)[0]?.name ?? 'idle'}
            </div>
            <div className="text-ink2 text-sm mb-3">
              {latest.source} · {latest.trigger} · {fmtTime(latest.ts)}
            </div>
            <details className="text-sm">
              <summary className="text-ink2 cursor-pointer">context</summary>
              <pre className="mt-2 text-xs bg-bg rounded p-2 overflow-x-auto
                              text-ink2 whitespace-pre-wrap">
                {JSON.stringify(parseContext(latest), null, 2)}
              </pre>
            </details>
          </>
        ) : (
          <div className="text-muted">Waiting for first cycle…</div>
        )}
      </StatCard>
    </div>
  )
}
