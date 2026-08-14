import { useEffect, useRef, useState } from 'react'

/** Reveals text character-by-character when it changes. First render shows
 *  the full text — only later changes animate. */
export function useTypewriter(text: string, msPerChar = 30): string {
  const [shown, setShown] = useState(text)
  const prev = useRef(text)
  useEffect(() => {
    if (prev.current === text) return
    prev.current = text
    let i = 0
    setShown('')
    const t = setInterval(() => {
      i += 1
      setShown(text.slice(0, i))
      if (i >= text.length) clearInterval(t)
    }, msPerChar)
    return () => clearInterval(t)
  }, [text, msPerChar])
  return shown
}
