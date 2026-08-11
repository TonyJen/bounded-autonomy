import { render, screen } from '@testing-library/react'
import App from '../App'

test('renders nav with three views', () => {
  render(<App />)
  expect(screen.getAllByText('Grok Guardian').length).toBeGreaterThan(0)
  expect(screen.getByRole('button', { name: 'room' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'agent' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'evals' })).toBeTruthy()
})
