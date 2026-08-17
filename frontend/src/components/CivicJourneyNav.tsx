import { Eye, Landmark, Lightbulb, List, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const primary = [
  { label: 'Agenda', to: '/civic', Icon: List },
  { label: 'Watch', to: '/watch', Icon: Eye },
  { label: 'Solutions', to: '/issues/housing-rent/solutions', Icon: Lightbulb },
  { label: 'ACT', to: '/act', Icon: Landmark },
  { label: 'Reps', to: '/politics/find-rep', Icon: Users },
] as const;

const desktop = [
  { label: 'Watch', to: '/watch' }, { label: 'Agenda', to: '/civic' },
  { label: 'Issues', to: '/issues/housing-rent' }, { label: 'Discuss', to: '/discuss' },
  { label: 'Elections', to: '/elections' }, { label: 'ACT', to: '/act' },
  { label: 'Solutions', to: '/issues/housing-rent/solutions' },
  { label: 'Representatives', to: '/politics/find-rep' },
] as const;

export default function CivicJourneyNav() {
  return <>
    <nav aria-label="Civic journey" className="hidden border-b border-border bg-bg/95 px-4 backdrop-blur md:block">
      <div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto py-2">{desktop.map((item) => <NavLink key={item.label} to={item.to} className={({ isActive }) => `shrink-0 rounded-pill px-3 py-2 text-xs font-semibold ${isActive ? 'bg-accent-dim text-accent-text' : 'text-text-2 hover:bg-surface hover:text-text-1'}`}>{item.label}</NavLink>)}</div>
    </nav>
    <nav aria-label="Primary" className="fixed inset-x-0 bottom-0 z-[70] border-t border-slate-300 bg-white/95 px-2 pb-[max(.35rem,env(safe-area-inset-bottom))] pt-1 text-slate-700 shadow-[0_-8px_24px_rgba(15,23,42,.14)] backdrop-blur md:hidden">
      <div className="mx-auto grid max-w-md grid-cols-5">{primary.map(({ label, to, Icon }) => <NavLink key={label} to={to} className={({ isActive }) => `flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-lg text-[11px] font-semibold ${isActive ? 'text-[#174f80]' : 'text-slate-500'}`}><Icon className="h-5 w-5" aria-hidden="true" /><span>{label}</span></NavLink>)}</div>
    </nav>
  </>;
}
