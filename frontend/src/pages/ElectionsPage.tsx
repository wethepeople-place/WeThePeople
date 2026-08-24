import { useEffect, useState } from 'react';
import { CalendarDays, ExternalLink, Landmark, LockKeyhole, MapPin, Search, Vote } from 'lucide-react';
import { Link } from 'react-router-dom';

import { fetchUpcomingElections, lookupElectionInformation, type ElectionLocation, type ElectionLookup } from '../api/civic';
import ForecastCard from '../components/ForecastCard';
import { US_STATE_NAMES } from '../data/usStateNames';

type ElectionItem = { id: string; name: string; election_day: string | null; division_id: string | null };

const stateOptions = Object.entries(US_STATE_NAMES).sort(([, first], [, second]) => first.localeCompare(second));
const electionState = (divisionId: string | null) => divisionId?.match(/\/state:([a-z]{2})(?:\/|$)/i)?.[1]?.toUpperCase() || null;
const isPublicElection = (item: ElectionItem) => !/\btest election\b/i.test(item.name);
const voteGovStateUrl = (stateCode: string) => `https://vote.gov/register/${US_STATE_NAMES[stateCode].toLowerCase().replaceAll(' ', '-')}`;
const EAC_POLLING_PLACE_URL = 'https://www.eac.gov/vote';
const EAC_ELECTION_OFFICE_URL = 'https://www.eac.gov/voters/register-and-vote-in-your-state';

const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('en-US', {
  month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
}).format(new Date(`${value}T00:00:00Z`)) : 'Date supplied by your election office';

const locationAddress = (item: ElectionLocation) => [item.address.locationName, item.address.line1, item.address.line2, item.address.city, item.address.state, item.address.zip].filter(Boolean).join(', ');

function OfficialFallbackLinks({ stateCode, compact = false }: { stateCode: string; compact?: boolean }) {
  const stateName = stateCode ? US_STATE_NAMES[stateCode] : '';
  const links = [
    { label: stateName ? `${stateName} voting rules` : 'State voting rules', description: 'Registration, deadlines, and voting options.', publisher: 'Vote.gov', url: stateCode ? voteGovStateUrl(stateCode) : 'https://vote.gov/' },
    { label: 'Find your polling place', description: 'Open your state’s official polling-place lookup.', publisher: 'U.S. Election Assistance Commission', url: EAC_POLLING_PLACE_URL },
    { label: 'Ballot and local election office', description: 'Find the official office that publishes sample ballots and local details.', publisher: 'U.S. Election Assistance Commission', url: EAC_ELECTION_OFFICE_URL },
  ];
  return <div className={compact ? 'mt-3 grid gap-2' : 'mt-4 grid gap-3'}>
    {links.map((link) => <a key={link.label} className="rounded-xl border border-slate-200 bg-white p-3 text-left outline-none transition hover:border-sky-300 focus-visible:ring-4 focus-visible:ring-sky-200" href={link.url} target="_blank" rel="noreferrer">
      <span className="flex items-start justify-between gap-2 font-bold text-[#174f80]">{link.label}<ExternalLink className="mt-0.5 h-4 w-4 shrink-0" /></span>
      {!compact && <span className="mt-1 block text-sm leading-5 text-slate-600">{link.description}</span>}
      <span className="mt-2 block text-[11px] font-semibold uppercase tracking-wide text-slate-500">Official source · {link.publisher}</span>
      <span className="mt-1 block text-[11px] text-slate-500">Live publisher page — confirm current details there</span>
    </a>)}
  </div>;
}

export default function ElectionsPage() {
  const [elections, setElections] = useState<ElectionItem[]>([]);
  const [catalogLoaded, setCatalogLoaded] = useState(false);
  const [catalogAvailability, setCatalogAvailability] = useState<'loading' | 'available' | 'stale' | 'unavailable'>('loading');
  const [catalogFetchedAt, setCatalogFetchedAt] = useState('');
  const [selectedState, setSelectedState] = useState('');
  const [address, setAddress] = useState('');
  const [result, setResult] = useState<ElectionLookup | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    fetchUpcomingElections()
      .then((data) => {
        setElections(data.items.filter(isPublicElection));
        // Keep the Pages-first rollout compatible with the currently deployed
        // API until the separately approved backend release adds availability.
        setCatalogAvailability(data.availability?.status || 'available');
        setCatalogFetchedAt(data.availability?.fetched_at || '');
      })
      .catch(() => { setElections([]); setCatalogAvailability('unavailable'); })
      .finally(() => setCatalogLoaded(true));
  }, []);

  const stateElections = selectedState ? elections.filter((item) => {
    const state = electionState(item.division_id);
    return state === selectedState || item.division_id === 'ocd-division/country:us';
  }) : [];
  const hasCoverage = stateElections.length > 0;

  const lookup = async (event: React.FormEvent) => {
    event.preventDefault();
    if (/^\s*\d{5}(?:-\d{4})?\s*$/.test(address)) {
      setResult(null);
      setNotice('Enter your full registered residential address, including street, city, state, and ZIP. A ZIP code alone cannot identify your ballot.');
      return;
    }
    setLoading(true); setNotice(''); setResult(null);
    try {
      setResult(await lookupElectionInformation(address, stateElections[0]?.id));
      setAddress('');
    }
    catch (reason) { setNotice(reason instanceof Error ? reason.message : 'Election information could not be loaded.'); }
    finally { setLoading(false); }
  };

  const locations = result ? [
    ['Election Day', result.polling_locations],
    ['Vote early', result.early_vote_sites],
    ['Ballot drop boxes', result.drop_off_locations],
  ] as const : [];

  return <main className="min-h-screen bg-[#eef1f5] pb-28 text-slate-950 md:pb-16">
    <header className="bg-[#214f78] px-5 py-7 text-white">
      <div className="mx-auto max-w-5xl"><p className="text-xs font-bold uppercase tracking-[.18em] text-sky-200">ACT · Elections</p><h1 className="mt-1 text-3xl font-black sm:text-5xl">Make your voting plan</h1><p className="mt-3 max-w-2xl leading-7 text-sky-50">Find what is on your ballot and where to vote. We use the address once for this lookup and do not save it.</p></div>
    </header>
    <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3"><CalendarDays className="mt-1 h-5 w-5 shrink-0 text-[#214f78]" /><div><h2 className="font-bold">Start with your state</h2><p className="mt-1 text-sm leading-6 text-slate-600">We check whether ballot data is available before asking for your private address.</p></div></div>
        <label className="mt-5 block text-sm font-bold" htmlFor="election-state">State or District of Columbia</label>
        <select id="election-state" value={selectedState} onChange={(event) => { setSelectedState(event.target.value); setAddress(''); setNotice(''); setResult(null); }} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 outline-none focus:ring-4 focus:ring-sky-200">
          <option value="">Select your state</option>
          {stateOptions.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
        </select>

        {catalogLoaded && catalogAvailability === 'unavailable' && <div role="alert" className="mt-5 rounded-xl bg-rose-50 p-4 text-rose-950">
          <h3 className="font-bold">Election provider is temporarily unavailable</h3>
          <p className="mt-1 text-sm leading-6">We cannot check ballot-data coverage right now, so your address is not requested or sent. This does not mean your state has no election.</p>
          <OfficialFallbackLinks stateCode={selectedState} compact />
        </div>}

        {catalogLoaded && catalogAvailability === 'stale' && <div role="status" className="mt-5 rounded-xl bg-sky-50 p-4 text-sky-950"><strong>Using the most recent available election catalog.</strong><p className="mt-1 text-sm leading-6">The provider could not refresh just now. Confirm all dates and ballot details with your election office.</p></div>}

        {catalogLoaded && catalogAvailability !== 'unavailable' && catalogFetchedAt && <p className="mt-3 text-xs text-slate-500">Official provider catalog refreshed {new Date(catalogFetchedAt).toLocaleString()}.</p>}

        {selectedState && catalogLoaded && catalogAvailability !== 'unavailable' && !hasCoverage && <div role="status" className="mt-5 rounded-xl bg-amber-50 p-4 text-amber-950">
          <h3 className="font-bold">Ballot data is not available here yet</h3>
          <p className="mt-1 text-sm leading-6">Our provider is not currently publishing election data for {US_STATE_NAMES[selectedState]}. Your address was not requested or sent.</p>
          <OfficialFallbackLinks stateCode={selectedState} compact />
        </div>}

        {selectedState && catalogAvailability !== 'unavailable' && hasCoverage && <div className="mt-5 border-t border-slate-200 pt-5">
          <div className="flex items-start gap-3"><LockKeyhole className="mt-1 h-5 w-5 shrink-0 text-emerald-700" /><div><h2 className="font-bold">Private full-address lookup</h2><p className="mt-1 text-sm leading-6 text-slate-600">Ballot data is available for {US_STATE_NAMES[selectedState]}. Enter your complete registered residential address. It is sent to the civic-information provider for this lookup only; WTP does not retain it, your registration status, or your choices.</p></div></div>
          <form onSubmit={lookup} className="mt-5 flex flex-col gap-3 sm:flex-row">
            <label className="sr-only" htmlFor="election-address">Full registered residential address</label>
            <input id="election-address" required minLength={5} maxLength={200} autoComplete="street-address" value={address} onChange={(event) => setAddress(event.target.value)} placeholder="Street address, city, state, ZIP" aria-describedby="election-address-help" className="min-h-12 flex-1 rounded-xl border border-slate-300 px-4 outline-none focus:ring-4 focus:ring-sky-200" />
            <button disabled={loading} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#dda91f] px-5 font-bold disabled:opacity-60"><Search className="h-5 w-5" />{loading ? 'Finding ballot…' : 'Find my election'}</button>
          </form>
          <p id="election-address-help" className="mt-2 text-xs text-slate-500">Include street, city, state, and ZIP.</p>
          {notice && <p role="alert" className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">{notice} Verify with your state or local election office.</p>}
        </div>}
      </section>

      {!result && <section className="mt-5 grid gap-3 md:grid-cols-2">
        <article className="rounded-2xl border border-slate-200 bg-white p-5"><CalendarDays className="h-6 w-6 text-[#214f78]" /><h2 className="mt-3 text-xl font-bold">Upcoming elections</h2>{catalogAvailability === 'unavailable' ? <p className="mt-2 text-slate-600">Coverage cannot be checked while the provider is unavailable. Use the official voter-services links.</p> : !selectedState ? <p className="mt-2 text-slate-600">Select your state to see relevant supported elections.</p> : stateElections.length ? <ul className="mt-3 space-y-3">{stateElections.map((item) => <li key={item.id} className="border-t border-slate-100 pt-3"><strong>{item.name}</strong><p className="text-sm text-slate-600">{formatDate(item.election_day)}</p></li>)}</ul> : <p className="mt-2 text-slate-600">No election for {US_STATE_NAMES[selectedState]} is currently published by our ballot-data provider.</p>}</article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5"><Landmark className="h-6 w-6 text-[#214f78]" /><h2 className="mt-3 text-xl font-bold">Official voter services</h2><p className="mt-2 leading-6 text-slate-600">Use live official sources for state rules, polling-place tools, sample-ballot publishers, and local election offices.</p><OfficialFallbackLinks stateCode={selectedState} /></article>
      </section>}

      {result && <div className="mt-5 space-y-5">
        <section className="rounded-2xl bg-[#214f78] p-5 text-white"><p className="text-xs font-bold uppercase tracking-widest text-sky-200">Your next election</p><h2 className="mt-2 text-2xl font-black">{result.election.name}</h2><p className="mt-1 text-sky-100">{formatDate(result.election.election_day)}</p></section>
        {locations.map(([title, items]) => items.length > 0 && <section key={title}><h2 className="flex items-center gap-2 text-xl font-black"><MapPin className="h-5 w-5 text-[#214f78]" />{title}</h2><div className="mt-3 grid gap-3 md:grid-cols-2">{items.map((item, index) => <article key={`${title}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-5"><h3 className="font-bold">{item.name || title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{locationAddress(item)}</p>{item.polling_hours && <p className="mt-2 text-sm font-semibold">{item.polling_hours}</p>}</article>)}</div></section>)}
        <section><h2 className="flex items-center gap-2 text-xl font-black"><Vote className="h-5 w-5 text-[#214f78]" />What is on your ballot</h2>{result.contests.length ? <div className="mt-3 space-y-3">{result.contests.map((contest, index) => <details key={`${contest.office}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-5"><summary className="cursor-pointer font-bold">{contest.office}{contest.district ? ` · ${contest.district}` : ''}</summary>{contest.candidates.length > 0 && <ul className="mt-3 space-y-2">{contest.candidates.map((candidate) => <li key={`${candidate.name}-${candidate.party || ''}`} className="text-sm"><strong>{candidate.name}</strong>{candidate.party ? ` · ${candidate.party}` : ''}</li>)}</ul>}{contest.forecast_token && <div className="mt-4"><ForecastCard compact contestToken={contest.forecast_token} question={`Who will win ${contest.office}${contest.district ? ` · ${contest.district}` : ''}?`} options={contest.candidates.map((candidate) => ({ key: candidate.forecast_key, label: candidate.name, party: candidate.party }))} /></div>}</details>)}</div> : <p className="mt-3 rounded-2xl bg-white p-5 text-slate-600">No contest list was supplied for this election. Use the official ballot link below.</p>}</section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-xl font-black">Verify with election officials</h2><div className="mt-3 grid gap-3">{result.election_authorities.map((office, index) => <article key={`${office.name}-${index}`}><h3 className="font-bold">{office.name}</h3><p className="text-sm text-slate-600">{office.region}</p><div className="mt-2 flex flex-wrap gap-4 text-sm font-bold text-[#174f80]">{office.registration_url && <a href={office.registration_url} target="_blank" rel="noreferrer">Register</a>}{office.registration_status_url && <a href={office.registration_status_url} target="_blank" rel="noreferrer">Check registration</a>}{office.voting_location_url && <a href={office.voting_location_url} target="_blank" rel="noreferrer">Voting locations</a>}{office.ballot_info_url && <a href={office.ballot_info_url} target="_blank" rel="noreferrer">Official ballot</a>}{office.election_info_url && <a href={office.election_info_url} target="_blank" rel="noreferrer">Election office</a>}</div></article>)}</div></section>
        <button type="button" onClick={() => { setResult(null); setAddress(''); }} className="min-h-11 font-bold text-[#174f80] underline">Clear this lookup</button>
      </div>}
      <p className="mt-8 text-center text-xs leading-5 text-slate-500">Election information can change. Always confirm deadlines, eligibility, ballot content, and voting locations with your state or local election office.</p>
      <Link to="/act" className="mt-4 flex min-h-12 items-center justify-center rounded-xl border border-[#214f78] font-bold text-[#214f78]">Back to ACT</Link>
    </div>
  </main>;
}
