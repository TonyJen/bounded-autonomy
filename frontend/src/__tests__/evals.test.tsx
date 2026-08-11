import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import EvalsView from '../views/EvalsView'
import { vi } from 'vitest'

const runResult = {
  run_id: 'r1',
  summary: { total: 5, passed: 5, failed: 0, average_score: 1.0,
             avg_latency_ms: 1234.5, total_input_tokens: 5000,
             total_output_tokens: 250 },
  results: [
    { case_id: 'heat_spike', passed: true, score: 1.0,
      detail: { required_ok: true, forbidden_ok: true, args_ok: true,
                called: ['set_fan'] },
      perf: { latency_ms: 1234.5, input_tokens: 1000, output_tokens: 50 } },
    { case_id: 'night_motion', passed: false, score: 0.5,
      detail: { required_ok: false, forbidden_ok: true, args_ok: true,
                called: ['set_fan'] },
      perf: { latency_ms: 2000, input_tokens: 1000, output_tokens: 50 } },
  ],
  comparison: { baseline: false },
}

vi.mock('../lib/api', () => ({
  api: {
    runEvals: vi.fn(() => Promise.resolve({ run_id: 'job1' })),
    getEvalRun: vi.fn(() => Promise.resolve({
      status: 'completed', result: runResult })),
    getEvalRecord: vi.fn(() => Promise.resolve({
      run_id: 'r1', summary: { total: 5, passed: 4, failed: 1,
                               average_score: 0.9, avg_latency_ms: 6400,
                               total_input_tokens: 9000,
                               total_output_tokens: 400 },
      results: [{ case_id: 'sensor_nan', passed: true, score: 1.0,
                  detail: { required_ok: true, forbidden_ok: true,
                            args_ok: true },
                  perf: { latency_ms: 6400, input_tokens: 1800,
                          output_tokens: 80 } }],
    })),
    getEvalHistory: vi.fn(() => Promise.resolve({ runs: [{
      run_id: 'r1', ts: '', mode: 'mock', model: 'mock',
      summary: { total: 5, passed: 5, failed: 0, average_score: 1.0,
                 avg_latency_ms: 6400 } }] })),
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

test('shows correctness breakdown and performance per case', async () => {
  render(<EvalsView />)
  fireEvent.click(screen.getByRole('button', { name: /run mock/i }))
  await screen.findByText(/heat_spike/)
  // correctness chips (req ✓ / forb ✓ / args ✓ per case; req ✗ on the failure)
  expect(screen.getAllByText(/req ✓/).length).toBeGreaterThan(0)
  expect(screen.getAllByText(/req ✗/).length).toBe(1)
  // per-case performance: latency + tokens
  expect(screen.getByText(/1\.2s · 1,000→50 tok/)).toBeTruthy()
  // summary aggregates
  expect(screen.getByText(/1\.2s avg/)).toBeTruthy()
  expect(screen.getByText(/5,000→250 tok/)).toBeTruthy()
})

test('clicking a history row drills into that run record', async () => {
  render(<EvalsView />)
  // history row renders, then click it
  const row = await screen.findByRole('button', { name: /r1/ })
  fireEvent.click(row)
  // the record's case + perf render, and the card shows the historical run id
  expect(await screen.findByText(/sensor_nan/)).toBeTruthy()
  expect(screen.getByText(/6\.4s · 1,800→80 tok/)).toBeTruthy()
  expect(screen.getByText(/Run r1/)).toBeTruthy()
})
