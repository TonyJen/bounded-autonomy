import { vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import RoomView from '../views/RoomView'

// mock the API + WS hooks
vi.mock('../lib/api', () => ({
  api: {
    getStatus: () => Promise.resolve({
      device: { online: true },
      sensors: { temp_c: 24.5, humidity_pct: 41, light: 612, motion: 0 },
      last_seen: new Date().toISOString(),
    }),
    simScenario: vi.fn(), simEvent: vi.fn(),
  },
}))
vi.mock('../lib/ws', () => ({ useGatewayWS: () => ({ connected: true }) }))

test('renders sensor gauges and scenario controls', async () => {
  render(<RoomView />)
  expect(await screen.findByText(/24\.5/)).toBeTruthy()
  expect(screen.getByText(/Temperature/i)).toBeTruthy()
  expect(screen.getByText(/Humidity/i)).toBeTruthy()
  expect(screen.getByText(/Light/i)).toBeTruthy()
  expect(screen.getByRole('button', { name: /heat spike/i })).toBeTruthy()
  expect(screen.getByRole('button', { name: /motion/i })).toBeTruthy()
})
