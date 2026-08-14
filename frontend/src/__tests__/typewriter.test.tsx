import { vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { useTypewriter } from '../lib/useTypewriter'
import { useChangeFlash } from '../lib/useChangeFlash'

function Tw({ text }: { text: string }) {
  return <div data-testid="tw">{useTypewriter(text)}</div>
}

test('first render shows the full text (no animation on mount)', () => {
  render(<Tw text="hello" />)
  expect(screen.getByTestId('tw').textContent).toBe('hello')
})

test('text change types in character by character', () => {
  vi.useFakeTimers()
  try {
    const { rerender } = render(<Tw text="old" />)
    rerender(<Tw text="NEW" />)
    expect(screen.getByTestId('tw').textContent).toBe('')
    act(() => { vi.advanceTimersByTime(65) }) // 2 chars at 30ms/char
    expect(screen.getByTestId('tw').textContent).toBe('NE')
    act(() => { vi.advanceTimersByTime(100) })
    expect(screen.getByTestId('tw').textContent).toBe('NEW')
  } finally {
    vi.useRealTimers()
  }
})

function Fl({ v }: { v: number }) {
  return <div data-testid="fl" className={useChangeFlash(v)} />
}

test('change flash applies the class briefly after a change', () => {
  vi.useFakeTimers()
  try {
    const { rerender } = render(<Fl v={1} />)
    expect(screen.getByTestId('fl').className).toBe('')
    rerender(<Fl v={2} />)
    expect(screen.getByTestId('fl').className).toBe('animate-valueflash')
    act(() => { vi.advanceTimersByTime(400) })
    expect(screen.getByTestId('fl').className).toBe('')
  } finally {
    vi.useRealTimers()
  }
})
