import { render, screen } from '@testing-library/react'
import AgentView from '../views/AgentView'
import { vi } from 'vitest'

vi.mock('../lib/api', () => ({
  api: { getHistory: () => Promise.resolve({
    snapshots: [],
    decisions: [{
      id: 1, ts: new Date().toISOString(), trigger: 'periodic', source: 'agent',
      context_json: '{}',
      tool_calls_json: JSON.stringify([{ name: 'set_fan', args: { on: true } }]),
      latency_ms: 6200, input_tokens: 1173, output_tokens: 46,
    }],
  }) },
}))
vi.mock('../lib/ws', () => ({ useGatewayWS: () => ({ connected: true }) }))

test('renders decision log with tool calls', async () => {
  render(<AgentView />)
  // 'set_fan' appears in both the log chip and the hero; 'agent' in badge + hero subline
  expect((await screen.findAllByText(/set_fan/)).length).toBeGreaterThan(0)
  expect(screen.getAllByText(/agent/i).length).toBeGreaterThan(0)
  expect(screen.getByText(/1,173/)).toBeTruthy()  // token count formatted
})
