import { useEffect, useRef, useState } from 'react'

/** Returns 'animate-valueflash' for 300ms after `value` changes ('' while
 *  idle and on first render). Pair with the valueflash keyframes. */
export function useChangeFlash(value: unknown): string {
  const [flash, setFlash] = useState(false)
  const prev = useRef(value)
  useEffect(() => {
    if (Object.is(prev.current, value)) return
    prev.current = value
    setFlash(true)
    const t = setTimeout(() => setFlash(false), 300)
    return () => clearTimeout(t)
  }, [value])
  return flash ? 'animate-valueflash' : ''
}
