import { NavLink } from 'react-router-dom';

const destinations = [
  { label: 'Watch', to: '/watch' },
  { label: 'Agenda', to: '/civic' },
  { label: 'Evidence', to: '/issues/housing-rent' },
  { label: 'Government', to: '/government' },
  { label: 'Courts', to: '/courts' },
  { label: 'Discuss', to: '/discuss' },
  { label: 'ACT', to: '/act' },
  { label: 'Solutions', to: '/issues/housing-rent/solutions' },
  { label: 'Your District', to: '/politics/find-rep' },
] as const;

export default function CivicJourneyNav() {
  return (
    <nav aria-label="Civic journey" className="border-b border-border bg-bg/95 px-4 backdrop-blur">
      <div className="mx-auto flex max-w-7xl gap-1 overflow-x-auto py-2">
        {destinations.map((destination) => (
          <NavLink
            key={destination.label}
            to={destination.to}
            className={({ isActive }) => `shrink-0 rounded-pill px-3 py-2 text-xs font-semibold transition-colors ${isActive ? 'bg-accent-dim text-accent-text' : 'text-text-2 hover:bg-surface hover:text-text-1'}`}
          >
            {destination.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
