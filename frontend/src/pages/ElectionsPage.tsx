import { useEffect, useRef, useState } from 'react';
import { BadgeCheck, Bike, Bus, CalendarDays, Car, CarTaxiFront, ClipboardCheck, ExternalLink, Footprints, IdCard, Landmark, LockKeyhole, MapPin, Search, Vote } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import { fetchUpcomingElections, lookupElectionInformation, type ElectionLocation, type ElectionLookup } from '../api/civic';
import ForecastCard from '../components/ForecastCard';
import { getOfficialStateCalendar } from '../data/stateElectionCalendars';
import { US_STATE_NAMES } from '../data/usStateNames';
import useEmbeddedFrameHeight from '../hooks/useEmbeddedFrameHeight';

const Taxi = CarTaxiFront;

type ElectionItem = {
  id: string; name: string; election_day: string | null; division_id: string | null;
  description: string | null; registration_deadline: string | null;
  source?: { name: string; url: string; kind: 'public_api' | 'official_calendar' };
};

const stateOptions = Object.entries(US_STATE_NAMES).sort(([, first], [, second]) => first.localeCompare(second));
const electionState = (divisionId: string | null) => divisionId?.match(/\/state:([a-z]{2})(?:\/|$)/i)?.[1]?.toUpperCase() || null;
const isPublicElection = (item: ElectionItem) => !/\btest election\b/i.test(item.name);
const voteGovStateUrl = (stateCode: string) => `https://vote.gov/register/${US_STATE_NAMES[stateCode].toLowerCase().replaceAll(' ', '-')}`;
const eacStateUrl = (stateCode: string) => `https://www.eac.gov/${US_STATE_NAMES[stateCode].toLowerCase().replaceAll(' ', '-')}-voter-info`;
const EAC_POLLING_PLACE_URL = 'https://www.eac.gov/vote';
const EAC_ELECTION_OFFICE_URL = 'https://www.eac.gov/voters/register-and-vote-in-your-state';
const GOOGLE_CIVIC_SOURCE = 'https://developers.google.com/civic-information';
const NO_ADDRESS_COVERAGE = 'Exact ballot and polling-place details are not available from the provider for this address right now.';

const ARKANSAS_ID_SOURCE = 'https://sos.arkansas.gov/elections/voter-information/voter-registration-information';
const ARKANSAS_ID_EXAMPLES = [
  'Driver’s license or other photo identification card',
  'U.S. passport or U.S. military identification',
  'Arkansas college or university employee/student photo ID',
  'Concealed-handgun license, qualifying public-assistance photo ID, or voter verification card',
];

const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('en-US', {
  month: 'long', day: 'numeric', year: 'numeric', timeZone: 'UTC',
}).format(new Date(`${value}T00:00:00Z`)) : 'Date supplied by your election office';

const catalogFreshness = (value: string) => {
  const updated = new Date(value);
  const today = new Date();
  const isToday = updated.getFullYear() === today.getFullYear()
    && updated.getMonth() === today.getMonth()
    && updated.getDate() === today.getDate();
  return isToday
    ? 'Election data updated today.'
    : `Election data last updated ${new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric' }).format(updated)}.`;
};

const mergeElectionCatalog = (liveItems: ElectionItem[], officialItems: ElectionItem[]) => {
  const liveDates = new Set(liveItems.map((item) => item.election_day).filter(Boolean));
  return [...liveItems, ...officialItems.filter((item) => !item.election_day || !liveDates.has(item.election_day))]
    .sort((first, second) => (first.election_day || '9999').localeCompare(second.election_day || '9999'));
};

const electionPresentation = (item: ElectionItem, stateCode: string) => {
  if (stateCode === 'IL' && item.election_day === '2027-02-23') {
    return {
      name: 'February 23, 2027 Consolidated Primary — only where applicable',
      description: 'This primary is held only in jurisdictions that require one. Your address and local election authority determine whether it applies to you.',
    };
  }
  return { name: item.name, description: item.description };
};

const locationAddress = (item: ElectionLocation) => [item.address.locationName, item.address.line1, item.address.line2, item.address.city, item.address.state, item.address.zip].filter(Boolean).join(', ');
const googleDirectionsUrl = (destination: string, travelMode: 'driving' | 'transit' | 'walking' | 'bicycling') => `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destination)}&travelmode=${travelMode}&dir_action=navigate&utm_source=wethepeople&utm_campaign=voting_directions`;
const uberRideUrl = (destination: string, nickname: string) => `https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff%5Bformatted_address%5D=${encodeURIComponent(destination)}&dropoff%5Bnickname%5D=${encodeURIComponent(nickname)}`;
const weatherUrl = (item: ElectionLocation, electionDay: string | null) => {
  const place = [item.address.city, item.address.state].filter(Boolean).join(', ');
  return `https://www.google.com/search?q=${encodeURIComponent(`weather ${place}${electionDay ? ` ${formatDate(electionDay)}` : ''}`)}`;
};

function OfficialFallbackLinks({ stateCode, compact = false }: { stateCode: string; compact?: boolean }) {
  const stateName = stateCode ? US_STATE_NAMES[stateCode] : '';
  const links = [
    { label: stateName ? `${stateName} voting rules` : 'State voting rules', description: 'Registration, deadlines, and voting options.', publisher: 'Vote.gov', url: stateCode ? voteGovStateUrl(stateCode) : 'https://vote.gov/' },
    { label: 'Check registration and polling place', description: 'Open official state links for registration status, polling locations, and voting hours.', publisher: 'U.S. Election Assistance Commission', url: stateCode ? eacStateUrl(stateCode) : EAC_POLLING_PLACE_URL },
    { label: 'What identification should I bring?', description: 'Check the current state requirements and accepted documents before leaving to vote.', publisher: stateCode === 'AR' ? 'Arkansas Secretary of State' : 'U.S. Election Assistance Commission', url: stateCode === 'AR' ? ARKANSAS_ID_SOURCE : (stateCode ? eacStateUrl(stateCode) : EAC_POLLING_PLACE_URL) },
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
  const [searchParams] = useSearchParams();
  const isEmbedded = searchParams.get('embed') === '1';
  const [elections, setElections] = useState<ElectionItem[]>([]);
  const [catalogLoaded, setCatalogLoaded] = useState(false);
  const [catalogAvailability, setCatalogAvailability] = useState<'loading' | 'available' | 'stale' | 'unavailable'>('loading');
  const [catalogFetchedAt, setCatalogFetchedAt] = useState('');
  const [selectedState, setSelectedState] = useState('');
  const [showAddressLookup, setShowAddressLookup] = useState(false);
  const [showStateInformation, setShowStateInformation] = useState(false);
  const [zipCode, setZipCode] = useState('');
  const [streetAddress, setStreetAddress] = useState('');
  const [result, setResult] = useState<ElectionLookup | null>(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const pageRef = useRef<HTMLElement | null>(null);

  useEmbeddedFrameHeight(isEmbedded, 'elections', pageRef);

  useEffect(() => {
    if (!selectedState) {
      setElections([]);
      setCatalogLoaded(true);
      setCatalogAvailability('available');
      return;
    }
    setCatalogLoaded(false);
    setCatalogAvailability('loading');
    fetchUpcomingElections(selectedState)
      .then((data) => {
        const liveItems = data.items.filter(isPublicElection);
        setElections(mergeElectionCatalog(liveItems, getOfficialStateCalendar(selectedState)));
        // Keep the Pages-first rollout compatible with the currently deployed
        // API until the separately approved backend release adds availability.
        setCatalogAvailability(data.availability?.status || 'available');
        setCatalogFetchedAt(data.availability?.fetched_at || '');
      })
      .catch(() => {
        const officialCalendar = getOfficialStateCalendar(selectedState);
        setElections(officialCalendar);
        setCatalogAvailability(officialCalendar.length ? 'stale' : 'unavailable');
      })
      .finally(() => setCatalogLoaded(true));
  }, [selectedState]);

  const stateElections = selectedState ? elections.filter((item) => {
    const state = electionState(item.division_id);
    return state === selectedState || item.division_id === 'ocd-division/country:us';
  }) : [];
  const hasCoverage = stateElections.length > 0;

  const lookup = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanZip = zipCode.trim();
    const cleanStreet = streetAddress.trim();
    if (!/^\d{5}(?:-\d{4})?$/.test(cleanZip)) {
      setResult(null);
      setNotice('Enter a valid 5-digit ZIP code.');
      return;
    }
    if (!/\d/.test(cleanStreet)) {
      setResult(null);
      setNotice('Add the house number with the street name so we can identify the correct voting precinct.');
      return;
    }
    setLoading(true); setNotice(''); setResult(null);
    try {
      const providerElectionId = stateElections.find((item) => /^\d+$/.test(item.id))?.id;
      setResult(await lookupElectionInformation(`${cleanStreet}, ${cleanZip}, ${selectedState}`, providerElectionId));
      setZipCode('');
      setStreetAddress('');
    }
    catch (reason) { setNotice(reason instanceof Error ? reason.message : 'Election information could not be loaded.'); }
    finally { setLoading(false); }
  };

  const locations = result ? [
    ['Election Day', result.polling_locations],
    ['Vote early', result.early_vote_sites],
    ['Ballot drop boxes', result.drop_off_locations],
  ] as const : [];

  const noAddressCoverage = notice.startsWith(NO_ADDRESS_COVERAGE);

  return <main ref={pageRef} className={`${isEmbedded ? 'act-embedded-theme pb-6' : 'min-h-screen bg-[#f5f5f7] pb-28 text-slate-950 md:pb-8'}`}>
    <header className={`${isEmbedded ? 'bg-[#111318] px-5 py-7 sm:px-8 sm:py-9' : 'bg-[#214f78] px-5 py-7'} text-white`}>
      <div className="mx-auto max-w-5xl"><p className={`text-xs font-bold uppercase tracking-[.2em] ${isEmbedded ? 'text-slate-500' : 'text-sky-200'}`}>ACT · Elections</p><h1 className={`${isEmbedded ? 'mt-2 text-3xl font-semibold tracking-[-0.03em] sm:text-5xl' : 'mt-1 text-3xl font-black sm:text-5xl'}`}>Cast your vote. Give change a chance.</h1><p className={`mt-3 max-w-2xl leading-7 ${isEmbedded ? 'text-slate-400' : 'text-sky-50'}`}>Success is never guaranteed. But if we do not try, failure is. Make your voting plan and take the first step.</p></div>
    </header>
    <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6">
      <section className="rounded-[22px] border border-black/[0.08] bg-white p-5 shadow-[0_12px_40px_rgba(15,23,42,0.07)] sm:p-6">
        <div className="flex items-start gap-3"><CalendarDays className="mt-1 h-5 w-5 shrink-0 text-[#214f78]" /><div><h2 className="font-bold">Start with your state</h2><p className="mt-1 text-sm leading-6 text-slate-600">We check whether ballot data is available before asking for your private address.</p></div></div>
        {!selectedState ? <><label className="mt-5 block text-sm font-bold" htmlFor="election-state">State or District of Columbia</label>
          <select id="election-state" value="" onChange={(event) => { const state = event.target.value; setSelectedState(state); setShowAddressLookup(Boolean(state)); setShowStateInformation(false); setZipCode(''); setStreetAddress(''); setNotice(''); setResult(null); }} className="mt-2 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-4 outline-none focus:ring-4 focus:ring-sky-200">
            <option value="">Select your state</option>
            {stateOptions.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
          </select></> : <div className="mt-5 flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-4"><div><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Your state</p><p className="font-bold">{US_STATE_NAMES[selectedState]}</p></div><button type="button" onClick={() => { setSelectedState(''); setShowAddressLookup(false); setShowStateInformation(false); setZipCode(''); setStreetAddress(''); setNotice(''); setResult(null); }} className="min-h-10 px-3 text-sm font-bold text-[#174f80] underline">Change</button></div>}

        {catalogLoaded && catalogAvailability === 'unavailable' && <div role="alert" className="mt-5 rounded-xl bg-rose-50 p-4 text-rose-950">
          <h3 className="font-bold">Election provider is temporarily unavailable</h3>
          <p className="mt-1 text-sm leading-6">We cannot check ballot-data coverage right now, so your address is not requested or sent. This does not mean your state has no election.</p>
          <OfficialFallbackLinks stateCode={selectedState} compact />
        </div>}

        {catalogLoaded && catalogAvailability === 'stale' && <div role="status" className="mt-5 rounded-xl bg-sky-50 p-4 text-sky-950"><strong>Using the most recent available election catalog.</strong><p className="mt-1 text-sm leading-6">The provider could not refresh just now. Confirm all dates and ballot details with your election office.</p></div>}

        {catalogLoaded && catalogAvailability !== 'unavailable' && catalogFetchedAt && <p className="mt-3 text-xs text-slate-500">{catalogFreshness(catalogFetchedAt)}</p>}

        {selectedState && catalogLoaded && catalogAvailability !== 'unavailable' && !hasCoverage && <div role="status" className="mt-5 rounded-xl bg-amber-50 p-4 text-amber-950">
          <h3 className="font-bold">Ballot data is not available here yet</h3>
          <p className="mt-1 text-sm leading-6">Our provider is not currently publishing election data for {US_STATE_NAMES[selectedState]}. Your address was not requested or sent.</p>
          <OfficialFallbackLinks stateCode={selectedState} compact />
        </div>}

        {selectedState && catalogAvailability !== 'unavailable' && hasCoverage && showAddressLookup && <div id="address-lookup" className="mt-5 border-t border-slate-200 pt-5">
          <div className="flex items-start gap-3"><LockKeyhole className="mt-1 h-5 w-5 shrink-0 text-emerald-700" /><div><h2 className="font-bold">Next: find your exact ballot and polling place</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-600"><li>We ask only for the details needed to identify your voting precinct.</li><li>The details are used once by the <a className="font-semibold text-[#174f80] underline" href={GOOGLE_CIVIC_SOURCE} target="_blank" rel="noreferrer">Google Civic Information API</a> and are not stored by WTP.</li></ul></div></div>
          <form onSubmit={lookup} className="mt-5 max-w-xl space-y-4">
            <div><label className="block text-sm font-bold" htmlFor="election-zip">1. ZIP code</label><input id="election-zip" required inputMode="numeric" maxLength={10} autoComplete="postal-code" value={zipCode} onChange={(event) => { const nextZip = event.target.value; setZipCode(nextZip); setNotice(''); const cleanZip = nextZip.replace(/\D/g, '').slice(0, 5); if (isEmbedded && cleanZip.length === 5) window.parent.postMessage({ type: 'wtp:act-zip', zip: cleanZip }, window.location.origin); }} placeholder="ZIP code" className="mt-2 min-h-12 w-full rounded-xl border border-slate-200 bg-[#f7f7f9] px-4 outline-none transition focus:border-slate-400 focus:bg-white focus:ring-4 focus:ring-slate-400/10" /></div>
            {/^\d{5}(?:-\d{4})?$/.test(zipCode.trim()) && <div><label className="block text-sm font-bold" htmlFor="election-street">2. House number and street</label><input id="election-street" required minLength={3} maxLength={120} autoComplete="address-line1" value={streetAddress} onChange={(event) => { setStreetAddress(event.target.value); setNotice(''); }} placeholder="Example: 126 Lamport Road" aria-describedby="election-street-help" className="mt-2 min-h-12 w-full rounded-xl border border-slate-200 bg-[#f7f7f9] px-4 outline-none transition focus:border-slate-400 focus:bg-white focus:ring-4 focus:ring-slate-400/10" /><p id="election-street-help" className="mt-2 text-xs leading-5 text-slate-500">The house number is required because voting precincts can split the same street. City and state are not requested again.</p><button disabled={loading} className="mt-4 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#292d33] px-5 font-bold text-white shadow-lg shadow-slate-950/10 transition hover:bg-[#343940] focus-visible:ring-4 focus-visible:ring-slate-400/15 disabled:opacity-60"><Search className="h-5 w-5" />{loading ? 'Finding ballot…' : 'Find my election'}</button></div>}
          </form>
          <button type="button" onClick={() => { setShowAddressLookup(false); setShowStateInformation(true); setZipCode(''); setStreetAddress(''); setNotice(''); }} className="mt-3 min-h-10 text-sm font-bold text-[#174f80] underline">Continue with state information</button>
          {notice && <div role="alert" className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">
            <strong>{noAddressCoverage ? 'Your official local details are not published here yet.' : 'We could not complete the lookup.'}</strong>
            <p className="mt-1 leading-6">{notice}{noAddressCoverage ? ' This does not mean there is no election.' : ''}</p>
            {noAddressCoverage ? <><OfficialFallbackLinks stateCode={selectedState} compact /><button type="button" onClick={() => { setShowAddressLookup(false); setShowStateInformation(true); setNotice(''); }} className="mt-3 min-h-10 font-bold text-[#174f80] underline">Continue with {US_STATE_NAMES[selectedState]} information</button></> : <p className="mt-2 leading-6">Try again shortly or use your state or local election office.</p>}
          </div>}
        </div>}
      </section>

      {!result && selectedState && showStateInformation && <section className="mt-5 grid gap-3 md:grid-cols-2">
        {hasCoverage && <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 md:col-span-2"><p className="text-sm font-semibold text-slate-700">Need precinct-level ballot and polling-place details?</p><button type="button" onClick={() => { setShowStateInformation(false); setShowAddressLookup(true); }} className="min-h-10 shrink-0 rounded-xl bg-[#dda91f] px-4 text-sm font-bold text-slate-950">Use my address</button></div>}
        <article className="rounded-2xl border border-slate-200 bg-white p-5"><CalendarDays className="h-6 w-6 text-[#214f78]" /><h2 className="mt-3 text-xl font-bold">Upcoming elections</h2>{catalogAvailability === 'loading' ? <p className="mt-2 text-slate-600">Checking public election calendars…</p> : catalogAvailability === 'unavailable' ? <p className="mt-2 text-slate-600">Live calendar sources could not be reached. Use the official voter-services links.</p> : !selectedState ? <p className="mt-2 text-slate-600">Select your state to see upcoming election dates, deadlines, and sources.</p> : stateElections.length ? <ul className="mt-3 space-y-3">{stateElections.map((item) => { const presentation = electionPresentation(item, selectedState); return <li key={item.id} className="border-t border-slate-100 pt-3 first:border-t-0 first:pt-0"><strong className="block">{presentation.name}</strong><p className="mt-1 text-sm font-semibold text-slate-700">{formatDate(item.election_day)}</p>{presentation.description && presentation.description !== presentation.name && <p className="mt-1 text-sm leading-5 text-slate-600">{presentation.description}</p>}{item.registration_deadline && <><p className="mt-2 text-xs text-slate-600">Provider-listed regular registration deadline: <strong>{formatDate(item.registration_deadline)}</strong></p><p className="mt-1 text-xs leading-5 text-slate-500">Deadlines vary by registration method. Later online, grace-period, or Election Day options may be available; verify the official state guidance.</p></>}{item.source && <a className="mt-2 inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wide text-[#174f80]" href={item.source.url} target="_blank" rel="noreferrer">Source · {item.source.name}<ExternalLink className="h-3.5 w-3.5" /></a>}</li>; })}</ul> : <div className="mt-3 rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-950"><strong>No published statewide date was returned.</strong><p>Local or special elections may still apply. Confirm with the official election office.</p></div>}</article>
        <article className="rounded-2xl border border-slate-200 bg-white p-5"><Landmark className="h-6 w-6 text-[#214f78]" /><h2 className="mt-3 text-xl font-bold">Official voter services</h2><p className="mt-2 leading-6 text-slate-600">Use live official sources for state rules, polling-place tools, sample-ballot publishers, and local election offices.</p><OfficialFallbackLinks stateCode={selectedState} /></article>
      </section>}

      {!result && selectedState && showStateInformation && <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3"><ClipboardCheck className="mt-1 h-6 w-6 shrink-0 text-[#214f78]" /><div><h2 className="text-xl font-black">Your voting checklist</h2><p className="mt-1 text-sm leading-6 text-slate-600">Complete these before Election Day. Requirements can change, so each item links to a live official source.</p></div></div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-xl bg-sky-50 p-4"><MapPin className="h-5 w-5 text-[#174f80]" /><h3 className="mt-2 font-bold">1. Confirm where to vote</h3><p className="mt-1 text-sm leading-6 text-slate-700">Use the address form above to get the exact building, full address, hours, and available early-voting locations.</p></article>
          <article className="rounded-xl bg-amber-50 p-4"><IdCard className="h-5 w-5 text-amber-800" /><h3 className="mt-2 font-bold">2. Bring required identification</h3>{selectedState === 'AR' ? <><p className="mt-1 text-sm leading-6 text-slate-700">Arkansas requires qualifying photo identification. Accepted examples include:</p><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">{ARKANSAS_ID_EXAMPLES.map((item) => <li key={item}>{item}</li>)}</ul><p className="mt-2 text-xs text-slate-600">If it has an expiration date, Arkansas says it must be current or expired no more than four years.</p><a className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-[#174f80] underline" href={ARKANSAS_ID_SOURCE} target="_blank" rel="noreferrer">Verify with Arkansas Secretary of State<ExternalLink className="h-3.5 w-3.5" /></a></> : <><p className="mt-1 text-sm leading-6 text-slate-700">Accepted documents differ by state. Check the official {US_STATE_NAMES[selectedState]} guidance before you leave.</p><a className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-[#174f80] underline" href={eacStateUrl(selectedState)} target="_blank" rel="noreferrer">See official state voter information<ExternalLink className="h-3.5 w-3.5" /></a></>}</article>
          <article className="rounded-xl bg-emerald-50 p-4"><BadgeCheck className="h-5 w-5 text-emerald-800" /><h3 className="mt-2 font-bold">3. Check registration and ballot</h3><p className="mt-1 text-sm leading-6 text-slate-700">Confirm your registration is active and review your official sample ballot before voting.</p><a className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-[#174f80] underline" href={eacStateUrl(selectedState)} target="_blank" rel="noreferrer">Registration and ballot links<ExternalLink className="h-3.5 w-3.5" /></a></article>
          <article className="rounded-xl bg-violet-50 p-4"><CalendarDays className="h-5 w-5 text-violet-800" /><h3 className="mt-2 font-bold">4. Plan the visit</h3><p className="mt-1 text-sm leading-6 text-slate-700">After the address lookup, use the official hours and location to plan when and how you’ll go. Weather and route options appear with the results.</p></article>
        </div>
      </section>}

      {result && <div className="mt-5 space-y-5">
        <section className="rounded-2xl bg-[#214f78] p-5 text-white"><p className="text-xs font-bold uppercase tracking-widest text-sky-200">Your next election</p><h2 className="mt-2 text-2xl font-black">{result.election.name}</h2><p className="mt-1 text-sky-100">{formatDate(result.election.election_day)}</p></section>
        {locations.map(([title, items]) => items.length > 0 && <section key={title}><h2 className="flex items-center gap-2 text-xl font-black"><MapPin className="h-5 w-5 text-[#214f78]" />{title}</h2><div className="mt-3 grid gap-3 md:grid-cols-2">{items.map((item, index) => { const fullAddress = locationAddress(item); const destinationName = item.name || title; const routes = [
          { label: 'Drive', mode: 'driving' as const, Icon: Car },
          { label: 'Transit', mode: 'transit' as const, Icon: Bus },
          { label: 'Walk', mode: 'walking' as const, Icon: Footprints },
          { label: 'Bike', mode: 'bicycling' as const, Icon: Bike },
        ]; return <article key={`${title}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-5"><h3 className="font-bold">{destinationName}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{fullAddress}</p>{item.polling_hours ? <p className="mt-2 text-sm font-semibold">Official hours: {item.polling_hours}</p> : <p className="mt-2 text-sm font-semibold text-amber-800">Hours were not supplied—confirm them with the election office before leaving.</p>}{item.start_date && <p className="mt-1 text-xs text-slate-600">Starts {formatDate(item.start_date)}</p>}{item.notes && <p className="mt-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-950">{item.notes}</p>}<div className="mt-4 rounded-xl bg-slate-50 p-4"><h4 className="text-sm font-black">Plan your visit</h4><dl className="mt-2 space-y-2 text-sm leading-5"><div><dt className="font-bold">What time should I come?</dt><dd className="text-slate-600">Mid-morning or mid-afternoon is often less busy than opening, lunchtime, and after work, but lines vary. Give yourself extra time and plan to arrive well before closing.</dd></div><div><dt className="font-bold">What should I wear?</dt><dd className="text-slate-600">Wear comfortable shoes and weather-appropriate layers. Avoid clothing with candidate or campaign messages unless the official election office confirms it is permitted.</dd></div><div><dt className="font-bold">What should I prepare?</dt><dd className="text-slate-600">Confirm registration, bring the required identification, review your sample ballot, charge your phone, and arrange any accessibility, childcare, or language assistance you may need.</dd></div></dl><a className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-[#174f80] underline" href={weatherUrl(item, result.election.election_day)} target="_blank" rel="noreferrer">Check the weather forecast<ExternalLink className="h-3.5 w-3.5" /></a></div>{fullAddress && <div className="mt-4 border-t border-slate-100 pt-4"><h4 className="text-sm font-black">How to get there</h4><p className="mt-1 text-xs leading-5 text-slate-500">Opens directions from your device’s current location. Availability depends on local services.</p><div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5">{routes.map(({ label, mode, Icon }) => <a key={mode} aria-label={`${label} directions to ${destinationName}`} className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2 text-xs font-bold text-[#174f80] hover:border-sky-300" href={googleDirectionsUrl(fullAddress, mode)} target="_blank" rel="noreferrer"><Icon className="h-4 w-4" />{label}</a>)}<a aria-label={`Request Uber to ${destinationName}`} className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg bg-black px-2 text-xs font-bold text-white" href={uberRideUrl(fullAddress, destinationName)} target="_blank" rel="noreferrer"><Taxi className="h-4 w-4" />Uber</a></div><p className="mt-2 text-[11px] leading-4 text-slate-500">WTP does not book or pay for transportation. Review the route, accessibility, availability, and fare in the provider app before confirming.</p></div>}</article>; })}</div></section>)}
        <section><h2 className="flex items-center gap-2 text-xl font-black"><Vote className="h-5 w-5 text-[#214f78]" />What is on your ballot</h2>{result.contests.length ? <div className="mt-3 space-y-3">{result.contests.map((contest, index) => <details key={`${contest.office}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-5"><summary className="cursor-pointer font-bold">{contest.office}{contest.district ? ` · ${contest.district}` : ''}</summary>{contest.candidates.length > 0 && <ul className="mt-3 space-y-2">{contest.candidates.map((candidate) => <li key={`${candidate.name}-${candidate.party || ''}`} className="text-sm"><strong>{candidate.name}</strong>{candidate.party ? ` · ${candidate.party}` : ''}</li>)}</ul>}{contest.forecast_token && <div className="mt-4"><ForecastCard compact contestToken={contest.forecast_token} question={`Who will win ${contest.office}${contest.district ? ` · ${contest.district}` : ''}?`} options={contest.candidates.map((candidate) => ({ key: candidate.forecast_key, label: candidate.name, party: candidate.party }))} /></div>}</details>)}</div> : <p className="mt-3 rounded-2xl bg-white p-5 text-slate-600">No contest list was supplied for this election. Use the official ballot link below.</p>}</section>
        <section className="rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-xl font-black">Verify with election officials</h2><div className="mt-3 grid gap-3">{result.election_authorities.map((office, index) => <article key={`${office.name}-${index}`}><h3 className="font-bold">{office.name}</h3><p className="text-sm text-slate-600">{office.region}</p><div className="mt-2 flex flex-wrap gap-4 text-sm font-bold text-[#174f80]">{office.registration_url && <a href={office.registration_url} target="_blank" rel="noreferrer">Register</a>}{office.registration_status_url && <a href={office.registration_status_url} target="_blank" rel="noreferrer">Check registration</a>}{office.voting_location_url && <a href={office.voting_location_url} target="_blank" rel="noreferrer">Voting locations</a>}{office.ballot_info_url && <a href={office.ballot_info_url} target="_blank" rel="noreferrer">Official ballot</a>}{office.election_info_url && <a href={office.election_info_url} target="_blank" rel="noreferrer">Election office</a>}</div></article>)}</div></section>
        <button type="button" onClick={() => { setResult(null); setZipCode(''); setStreetAddress(''); }} className="min-h-11 font-bold text-[#174f80] underline">Clear this lookup</button>
      </div>}
      <p className="mt-8 text-center text-xs leading-5 text-slate-500">Election information can change. Always confirm deadlines, eligibility, ballot content, and voting locations with your state or local election office.</p>
      {!isEmbedded && <section className="mt-6 rounded-2xl bg-[#214f78] p-5 text-white shadow-sm">
        <h2 className="text-xl font-black">Want to do both?</h2>
        <p className="mt-1 text-sm leading-6 text-sky-50">You can also find the public officials who represent you and learn how to contact them.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2"><Link to="/politics/find-rep" className="flex min-h-12 items-center justify-center rounded-xl bg-[#dda91f] px-4 font-bold text-slate-950">Find my representatives</Link><Link to="/act" className="flex min-h-12 items-center justify-center rounded-xl border border-white/50 px-4 font-bold text-white">Back to ACT choices</Link></div>
      </section>}
    </div>
  </main>;
}
