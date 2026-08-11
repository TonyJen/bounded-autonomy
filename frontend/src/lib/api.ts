async function req(path: string, init?: RequestInit) {
  const resp = await fetch(path, init)
  if (!resp.ok) throw new Error(`${path} -> ${resp.status}`)
  return resp.json()
}

export const api = {
  getStatus: () => req('/status'),
  getHistory: (limit = 20) => req(`/history?limit=${limit}`),
  runEvals: (mode: 'mock' | 'live') =>
    req('/evals/run', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }) }),
  getEvalRun: (id: string) => req(`/evals/run/${id}`),
  getEvalRecord: (id: string) => req(`/evals/record/${id}`),
  getEvalHistory: (limit = 10) => req(`/evals/history?limit=${limit}`),
  simScenario: (name: string) =>
    req('/sim/scenario', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }) }),
  simEvent: (trigger: 'motion' | 'heat' | 'dark') =>
    req('/sim/event', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trigger }) }),
}
