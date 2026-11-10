import { Briefcase, ChartNoAxesCombined, Eye, Landmark, List, Users, Vote } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useEffect } from 'react';

type JourneyItem = {
  label: string;
  to: string;
  Icon: typeof List;
  external?: boolean;
};

const primary: JourneyItem[] = [
  { label: 'Agenda', to: '/civic', Icon: List },
  { label: 'Watch', to: '/videos', Icon: Eye },
  { label: 'Elections', to: '/elections', Icon: Vote },
  { label: 'ACT', to: '/act', Icon: Landmark },
  { label: 'Reps', to: '/politics/find-rep', Icon: Users },
  { label: 'Jobs', to: 'https://research.wethepeople.place/gov-salaries', Icon: Briefcase, external: true },
  { label: 'Bets', to: '/forecasts', Icon: ChartNoAxesCombined },
];

const desktop: Array<{ label: string; to: string; external?: boolean }> = [
  { label: 'Watch', to: '/videos' },
  { label: 'Agenda', to: '/civic' },
  { label: 'Issues', to: '/issues/housing-rent' },
  { label: 'Elections', to: '/elections' },
  { label: 'ACT', to: '/act' },
  { label: 'Jobs', to: 'https://research.wethepeople.place/gov-salaries', external: true },
  { label: 'Bets', to: '/forecasts' },
];

export default function CivicJourneyNav() {
  useEffect(() => {
    const previousPadding = document.body.style.paddingBottom;
    document.body.style.paddingBottom = '96px';
    return () => { document.body.style.paddingBottom = previousPadding; };
  }, []);

  return <>
    <nav aria-label="Civic journey" className="hidden border-b border-border bg-bg/95 px-4 backdrop-blur md:block">
      <div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto py-2">
        {desktop.map((item) => {
          const className = 'shrink-0 rounded-pill px-3 py-2 text-xs font-semibold text-text-2 hover:bg-surface hover:text-text-1';
          return item.external
            ? <a key={item.label} href={item.to} className={className}>{item.label}</a>
            : <NavLink key={item.label} to={item.to} className={({ isActive }) => `shrink-0 rounded-pill px-3 py-2 text-xs font-semibold ${isActive ? 'bg-accent-dim text-accent-text' : 'text-text-2 hover:bg-surface hover:text-text-1'}`}>{item.label}</NavLink>;
        })}
      </div>
    </nav>
    <nav aria-label="Primary" className="fixed inset-x-0 bottom-0 z-[70] border-t border-slate-300 bg-white/95 px-2 pb-[max(.35rem,env(safe-area-inset-bottom))] pt-1 text-slate-700 shadow-[0_-8px_24px_rgba(15,23,42,.14)] backdrop-blur md:inset-x-auto md:bottom-4 md:left-1/2 md:w-[min(1100px,calc(100vw-2rem))] md:-translate-x-1/2 md:rounded-2xl md:border md:px-3 md:py-1">
      <div className="mx-auto grid max-w-4xl" style={{ gridTemplateColumns: `repeat(${primary.length}, minmax(0, 1fr))` }}>
        {primary.map((item) => {
          const content = <><item.Icon className="h-5 w-5 md:h-6 md:w-6" aria-hidden="true" /><span>{item.label}</span></>;
          const shared = 'flex min-h-14 min-w-11 flex-col items-center justify-center gap-0.5 rounded-lg px-0.5 text-[10px] font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[#174f80] sm:text-[11px] md:min-h-16 md:text-xs';
          return item.external
            ? <a key={item.label} href={item.to} className={`${shared} text-slate-500 hover:bg-slate-50`}>{content}</a>
            : <NavLink key={item.label} to={item.to} className={({ isActive }) => `${shared} ${isActive ? 'bg-sky-50 text-[#174f80]' : 'text-slate-500 hover:bg-slate-50'}`}>{content}</NavLink>;
        })}
      </div>
    </nav>
  </>;
}
