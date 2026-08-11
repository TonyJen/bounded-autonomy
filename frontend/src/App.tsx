import { useEffect, useState } from 'react'
import RoomView from './views/RoomView'

type Tab = 'room' | 'agent' | 'evals'

export default function App() {
  const [tab, setTab] = useState<Tab>('room')
  return (
    <div className="min-h-screen bg-bg text-ink flex flex-col">
      <header className="flex items-center gap-6 px-6 py-4 border-b border-cardborder">
        <span className="text-lg font-semibold">Grok Guardian</span>
        <nav className="flex gap-2">
          {(['room', 'agent', 'evals'] as Tab[]).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-md capitalize ${
                tab === t ? 'bg-card text-ink' : 'text-ink2 hover:text-ink'}`}>
              {t}
            </button>
          ))}
        </nav>
      </header>
      <main className="flex-1 p-6">
        {tab === 'room' && <RoomView />}
        {tab === 'agent' && <div>Agent view (Task 5)</div>}
        {tab === 'evals' && <div>Evals view (Task 6)</div>}
      </main>
      <footer className="flex justify-between px-6 py-2 border-t border-cardborder text-muted text-sm">
        <span>Grok Guardian</span>
        <Clock />
      </footer>
    </div>
  )
}

function Clock() {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return <span>{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
}
