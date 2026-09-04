import { BarChart3, Landmark, List, MessageCircle, Play, SquarePen, Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';

const primary = [
  { label: 'Discuss', to: '/discuss', Icon: MessageCircle },
  { label: 'Videos', to: '/videos', Icon: Play },
  { label: 'Agenda', to: '/civic', Icon: List },
  { label: 'ACT', to: '/act', Icon: Landmark },
  { label: 'Reps', to: '/politics/find-rep', Icon: Users },
  { label: 'Forecasts', to: '/forecasts', Icon: BarChart3 },
] as const;

const desktop = [
  { label: 'Discuss', to: '/discuss' }, { label: 'Videos', to: '/videos' }, { label: 'Proposals', to: '/proposals' }, { label: 'Agenda', to: '/civic' },
  { label: 'Issues', to: '/issues/housing-rent' },
  { label: 'Post', to: '/discuss?compose=1#composer' },
  { label: 'Elections', to: '/elections' }, { label: 'ACT', to: '/act' },
  { label: 'Representatives', to: '/politics/find-rep' },
  { label: 'Jobs', to: 'https://research.wethepeople.place/gov-salaries' },
  { label: 'Forecasts', to: '/forecasts' },
] as const;

export default function CivicJourneyNav() {
  return <>
    <nav aria-label="Civic journey" className="hidden border-b border-border bg-bg/95 px-4 backdrop-blur md:block">
      <div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto py-2">{desktop.map((item) => <NavLink key={item.label} to={item.to} className={({ isActive }) => `shrink-0 rounded-pill px-3 py-2 text-xs font-semibold ${isActive ? 'bg-accent-dim text-accent-text' : 'text-text-2 hover:bg-surface hover:text-text-1'}`}>{item.label}</NavLink>)}</div>
    </nav>
    <nav aria-label="Primary" className="fixed inset-x-0 bottom-0 z-[70] border-t border-slate-300 bg-white/95 px-2 pb-[max(.35rem,env(safe-area-inset-bottom))] pt-1 text-slate-700 shadow-[0_-8px_24px_rgba(15,23,42,.14)] backdrop-blur md:hidden">
      <div className="mx-auto grid max-w-md grid-cols-6">{primary.map((item) => {
        const content = <><item.Icon className="h-5 w-5" aria-hidden="true" /><span>{item.label}</span></>;
        const shared = 'flex min-h-14 min-w-11 flex-col items-center justify-center gap-0.5 rounded-lg px-0.5 text-[10px] font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[#174f80]';
        return 'external' in item && item.external
          ? <a key={item.label} href={item.to} className={`${shared} text-slate-500`}>{content}</a>
          : <NavLink key={item.label} to={item.to} className={({ isActive }) => `${shared} ${isActive ? 'text-[#174f80]' : 'text-slate-500'}`}>{content}</NavLink>;
      })}</div>
    </nav>
    <NavLink to="/discuss?compose=1#composer" aria-label="Create a civic post" className="fixed bottom-[4.75rem] left-1/2 z-[69] flex min-h-12 -translate-x-1/2 items-center gap-2 rounded-full bg-[#dda91f] px-5 font-black text-slate-950 shadow-lg shadow-slate-950/25 outline-none focus-visible:ring-4 focus-visible:ring-sky-300 md:hidden"><SquarePen className="h-5 w-5" />Post</NavLink>
  </>;
}
