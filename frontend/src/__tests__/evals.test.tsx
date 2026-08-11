import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import EvalsView from '../views/EvalsView'
import { vi } from 'vitest'

const runResult = {
  run_id: 'r1', summary: { total: 5, passed: 5, failed: 0, average_score: 1.0 },
  results: [
    { case_id: 'heat_spike', passed: true, score: 1.0, detail: {} },
    { case_id: 'night_motion', passed: false, score: 0.5, detail: {} },
  ],
  comparison: { baseline: false },
}

vi.mock('../lib/api', () => ({
  api: {
    runEvals: vi.fn(() => Promise.resolve({ run_id: 'job1' })),
    getEvalRun: vi.fn(() => Promise.resolve({
      status: 'completed', result: runResult })),
    getEvalHistory: vi.fn(() => Promise.resolve({ runs: [{
      run_id: 'r1', ts: '', mode: 'mock', model: 'mock',
      summary: { total: 5, passed: 5, failed: 0, average_score: 1.0 } }] })),
  },
}))
vi.mock('../lib/ws', () => ({ useGatewayWS: () => ({ connected: true }) }))

test('runs evals and shows per-case results', async () => {
  render(<EvalsView />)
  fireEvent.click(screen.getByRole('button', { name: /run mock/i }))
  expect(await screen.findByText(/heat_spike/)).toBeTruthy()
  // '5/5' appears in both the latest-run summary and the history row
  expect(screen.getAllByText(/5\/5/).length).toBeGreaterThan(0)
})
