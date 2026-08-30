import { useEffect, useState } from 'react';
import { CalendarDays, ExternalLink, Landmark, ShieldCheck, Vote } from 'lucide-react';
import { Link } from 'react-router-dom';

import { fetchExternalForecasts, fetchOpenForecasts, type ExternalForecastMarket, type ForecastMarket } from '../api/civic';

type Filter = 'all' | 'bill' | 'election';

const closeLabel = (value: string) => new Intl.DateTimeFormat('en-US', {
  month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC',
}).format(new Date(value));

const observedLabel = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'recently' : new Intl.DateTimeFormat('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }).format(date);
};

export default function ForecastDiscoveryPage() {
  const [filter, setFilter] = useState<Filter>('all');
  const [markets, setMarkets] = useState<ForecastMarket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [external, setExternal] = useState<ExternalForecastMarket[]>([]);
  const [externalError, setExternalError] = useState(false);

  useEffect(() => {
    setLoading(true); setError('');
    fetchOpenForecasts(filter === 'all' ? undefined : filter)
      .then((data) => setMarkets(data.items))
      .catch((reason) => { setMarkets([]); setError(reason instanceof Error ? reason.message : 'Forecasts could not be loaded.'); })
      .finally(() => setLoading(false));
  }, [filter]);

  useEffect(() => {
    fetchExternalForecasts().then((data) => { setExternal(data.items.filter((item) => Array.isArray(item.outcomes))); setExternalError(false); })
      .catch(() => { setExternal([]); setExternalError(true); });
  }, []);

  return <main className="min-h-screen bg-[#eef1f5] pb-28 text-slate-950 md:pb-16">
    <header className="bg-[#153d7a] px-5 py-7 text-white"><div className="mx-auto max-w-5xl"><p className="text-xs font-black uppercase tracking-[.18em] text-blue-100">Civic Forecasts</p><h1 className="mt-1 text-3xl font-black sm:text-5xl">Open questions</h1><p className="mt-3 max-w-2xl leading-7 text-blue-50">Explore real civic questions already opened by participants. Civic Forecasts are free predictions for civic learning—not bets or financial contracts.</p></div></header>
    <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-start gap-3"><ShieldCheck className="mt-1 h-5 w-5 shrink-0 text-emerald-700" /><div><h2 className="font-bold">Choices stay private</h2><p className="mt-1 text-sm leading-6 text-slate-600">Individual choices are never listed. Totals and shares appear only after at least five people participate; before then, even the response count stays hidden.</p></div></div></section>
      <p className="mt-3 text-sm leading-6 text-slate-600">WeThePeople does not accept bets or provide money, prizes, payouts, transferable credits, or financial contracts. Forecasts are not polls, endorsements, official results, or voting advice.</p>

      <div aria-label="Forecast type" className="mt-5 flex gap-2 overflow-x-auto pb-1">{(['all', 'bill', 'election'] as const).map((item) => <button key={item} type="button" aria-pressed={filter === item} onClick={() => setFilter(item)} className={`min-h-11 shrink-0 rounded-full px-5 font-bold ${filter === item ? 'bg-[#214f78] text-white' : 'border border-slate-300 bg-white text-[#214f78]'}`}>{item === 'all' ? 'All open' : item === 'bill' ? 'Bills' : 'Elections'}</button>)}</div>

      {loading && <p role="status" className="mt-8 text-slate-600">Loading open civic questions…</p>}
      {error && <p role="alert" className="mt-8 rounded-xl bg-rose-50 p-4 text-rose-950">Forecast discovery is temporarily unavailable. No choices or participation data were exposed.</p>}
      {!loading && !error && markets.length === 0 && <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center"><h2 className="text-xl font-bold">No open {filter === 'all' ? 'forecasts' : `${filter} forecasts`} yet</h2><p className="mt-2 text-slate-600">Questions appear only after a real participant opens one from a tracked bill or supported official ballot contest.</p></section>}

      <section aria-label="Open forecasts" className="mt-5 grid gap-4 md:grid-cols-2">{markets.map((market) => {
        const visible = market.response_count !== null;
        const destination = market.market_type === 'bill' ? `/politics/bill/${encodeURIComponent(market.subject_id)}` : market.source_url;
        return <article key={market.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3"><span className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-widest text-[#214f78]">{market.market_type === 'bill' ? <Landmark aria-hidden="true" className="h-4 w-4" /> : <Vote aria-hidden="true" className="h-4 w-4" />}{market.market_type}</span><span className="inline-flex items-center gap-1 text-xs text-slate-500"><CalendarDays aria-hidden="true" className="h-4 w-4" />Closes {closeLabel(market.closes_at)}</span></div>
          <h2 className="mt-3 text-xl font-black leading-7">{market.question}</h2>
          <div className="mt-4 space-y-2">{market.options.map((option) => <div key={option.key} className="rounded-xl bg-slate-50 px-3 py-2"><div className="flex justify-between gap-3 text-sm"><strong>{option.label}{option.party ? ` · ${option.party}` : ''}</strong><span>{visible ? `${option.share}%` : 'Private'}</span></div>{visible && <div role="progressbar" aria-label={`${option.label} share`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={option.share || 0} className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-[#dda91f]" style={{ width: `${option.share || 0}%` }} /></div>}</div>)}</div>
          <p className="mt-4 text-sm text-slate-600">{visible ? `${market.response_count} responses · aggregate threshold met` : `Participation remains private until ${market.privacy_threshold} responses.`}</p>
          {market.current_user_choice && <p className="mt-2 text-sm font-bold text-emerald-800">Your private choice is saved.</p>}
          {market.market_type === 'bill' ? <Link to={destination} className="mt-4 inline-flex min-h-11 items-center font-bold text-[#174f80] underline">Open tracked bill</Link> : <a href={destination} target="_blank" rel="noreferrer" className="mt-4 inline-flex min-h-11 items-center gap-2 font-bold text-[#174f80] underline">Official election source <ExternalLink className="h-4 w-4" /></a>}
        </article>;
      })}</section>

      <section className="mt-9" aria-labelledby="external-forecast-heading">
        <p className="text-xs font-black uppercase tracking-[.18em] text-[#214f78]">External market signal</p>
        <h2 id="external-forecast-heading" className="mt-1 text-2xl font-black">Polymarket probabilities</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Automatically imported public market data. These prices reflect trading activity—not a poll, endorsement, fact, or WeThePeople prediction. An automated quality bot continuously checks activity, rules, dates, and price consistency and removes failing markets.</p>
        {externalError && <p className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">External market data is temporarily unavailable. Community Forecasts are unaffected.</p>}
        {!externalError && external.length === 0 && <p className="mt-4 rounded-xl border border-dashed border-slate-300 bg-white p-5 text-slate-600">No external markets currently pass the automated quality checks.</p>}
        <div className="mt-4 grid gap-4 md:grid-cols-2">{external.map((market) => <article key={market.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-xs font-black uppercase tracking-widest text-[#214f78]">Polymarket</span><span className="text-xs text-slate-500">Checked {observedLabel(market.observed_at)}</span></div>
          <h3 className="mt-3 text-xl font-black leading-7">{market.question}</h3>
          <div className="mt-4 space-y-2">{market.outcomes.map((outcome) => <div key={outcome.label} className="rounded-xl bg-slate-50 px-3 py-2"><div className="flex justify-between gap-3 text-sm"><strong>{outcome.label}</strong><span>{outcome.probability}%</span></div><div role="progressbar" aria-label={`${outcome.label} market-implied probability`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={outcome.probability} className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-[#dda91f]" style={{ width: `${outcome.probability}%` }} /></div></div>)}</div>
          <p className="mt-4 text-sm text-slate-600">Volume ${Math.round(market.volume).toLocaleString()} · Liquidity ${Math.round(market.liquidity).toLocaleString()} · Closes {closeLabel(market.closes_at)}</p>
          <a href={market.source_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex min-h-11 items-center gap-2 font-bold text-[#174f80] underline">View market and resolution rules <ExternalLink className="h-4 w-4" /></a>
        </article>)}</div>
      </section>
      <Link to="/act" className="mt-8 flex min-h-12 items-center justify-center rounded-xl border border-[#214f78] font-bold text-[#214f78]">Back to ACT</Link>
    </div>
  </main>;
}
