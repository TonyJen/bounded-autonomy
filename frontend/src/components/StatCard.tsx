import { ReactNode } from 'react'

export default function StatCard({ title, children, className = '' }: {
  title: string; children: ReactNode; className?: string
}) {
  return (
    <div className={`bg-card border border-cardborder rounded-xl p-4 ${className}`}>
      <div className="text-ink2 text-sm mb-2">{title}</div>
      {children}
    </div>
  )
}
