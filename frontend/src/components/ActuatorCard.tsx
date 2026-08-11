type Props = { name: string; icon: string; state: string; active: boolean }

export default function ActuatorCard({ name, icon, state, active }: Props) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-cardborder last:border-0">
      <span className="text-xl" aria-hidden>{icon}</span>
      <span className="text-ink flex-1">{name}</span>
      <span className={`text-sm px-2 py-0.5 rounded-full ${
        active ? 'bg-good/20 text-good' : 'bg-cardborder text-ink2'}`}>
        {state}
      </span>
    </div>
  )
}
