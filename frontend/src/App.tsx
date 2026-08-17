import { useEffect, useState } from 'react'
import RoomView from './views/RoomView'
import DeviceView from './views/DeviceView'
import AgentView from './views/AgentView'
import EvalsView from './views/EvalsView'

type Tab = 'room' | 'device' | 'agent' | 'evals'
const TABS: Tab[] = ['room', 'device', 'agent', 'evals']

function tabFromHash(): Tab {
  const h = window.location.hash.slice(1) as Tab
  return TABS.includes(h) ? h : 'room'
}

export default function App() {
  // tab rides the URL hash so refresh/sharing preserves the view
  const [tab, setTab] = useState<Tab>(tabFromHash)
  useEffect(() => { window.location.hash = tab }, [tab])
  return (
    <div className="min-h-screen bg-bg text-ink flex flex-col">
      <header className="flex items-center gap-6 px-6 py-4 border-b border-cardborder">
        <img src="/icon.svg" alt="Grok Guardian logo" className="w-8 h-8" />
        <span className="text-lg font-semibold">Grok Guardian</span>
        <nav className="flex gap-2">
          {TABS.map((t) => (
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
        {tab === 'device' && <DeviceView />}
        {tab === 'agent' && <AgentView />}
        {tab === 'evals' && <EvalsView />}
      </main>
      <footer className="flex justify-between items-center px-6 py-2 border-t border-cardborder text-muted text-sm">
        <span className="flex items-center gap-2">
          <img src="/icon.svg" alt="" className="w-4 h-4" />
          Grok Guardian
        </span>
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
