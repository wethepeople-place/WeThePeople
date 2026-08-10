import { Link } from 'react-router-dom';

const destinations = [
  { to: '/politics/legislation', title: 'Legislation', description: 'Follow bills, sponsors, actions, amendments, and authoritative congressional sources.' },
  { to: '/politics/activity', title: 'Votes and activity', description: 'Review votes, legislative actions, and other recent government activity.' },
  { to: '/politics/committees', title: 'Committees', description: 'See the committees and memberships that shape legislation.' },
  { to: '/politics/people', title: 'Public officials', description: 'Explore sourced profiles, sponsored bills, votes, and committee work.' },
  { to: '/politics/states', title: 'States', description: 'Browse state-level representatives and legislative activity.' },
  { to: '/politics/contracts', title: 'Contracts', description: 'Inspect government contract awards and their recipients.' },
  { to: '/politics/enforcement', title: 'Enforcement', description: 'Review public enforcement activity and official records.' },
  { to: '/politics/find-rep', title: 'Your district', description: 'Find the representatives responsible for acting on an issue.' },
] as const;

export default function GovernmentPage() {
  return (
    <main className="min-h-screen bg-bg px-5 py-12 text-text-1">
      <div className="mx-auto max-w-5xl">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Government</p>
        <h1 className="mt-3 font-display text-4xl sm:text-5xl">Public decisions and responsible institutions</h1>
        <p className="mt-3 max-w-3xl text-text-2">Move from a civic issue into sourced legislation, votes, committees, officials, public spending, enforcement, and representative action.</p>

        <section className="mt-10 grid gap-5 sm:grid-cols-2" aria-label="Government activity">
          {destinations.map((destination) => (
            <Link key={destination.to} to={destination.to} className="rounded-card border border-border bg-surface p-6 transition-colors hover:border-accent/60">
              <h2 className="text-xl font-semibold">{destination.title}</h2>
              <p className="mt-2 leading-6 text-text-2">{destination.description}</p>
              <span className="mt-5 inline-block text-sm font-semibold text-accent-text">Explore {destination.title.toLowerCase()} →</span>
            </Link>
          ))}
        </section>

        <aside className="mt-10 rounded-card border border-border bg-surface p-6">
          <h2 className="text-xl font-semibold">Legal proceedings are tracked separately</h2>
          <p className="mt-2 text-text-2">Court filings, allegations, procedural events, decisions, and appeals retain their distinct legal status and authoritative sources.</p>
          <Link className="mt-4 inline-block text-accent-text underline" to="/courts">Explore Courts</Link>
        </aside>
      </div>
    </main>
  );
}
