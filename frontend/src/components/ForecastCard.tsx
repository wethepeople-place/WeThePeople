import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, CheckCircle2 } from 'lucide-react';
import { fetchBillForecast, fetchElectionForecast, setBillForecast, setElectionForecast, type ForecastMarket } from '../api/civic';

type Option = { key: string; label: string; party?: string | null };

interface Props {
  billId?: string;
  contestToken?: string | null;
  question?: string;
  options?: Option[];
  compact?: boolean;
}

export default function ForecastCard({ billId, contestToken, question, options = [], compact = false }: Props) {
  const [market, setMarket] = useState<ForecastMarket | null>(null);
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (billId) fetchBillForecast(billId).then(setMarket).catch(() => undefined);
    else if (contestToken) fetchElectionForecast(contestToken).then(setMarket).catch(() => undefined);
  }, [billId, contestToken]);

  const initialOptions = options.length ? options : (billId ? [{ key: 'yes', label: 'Yes' }, { key: 'no', label: 'No' }] : []);
  const visibleOptions = market?.options || initialOptions.map((option) => ({ ...option, responses: null, share: null }));
  const forecastQuestion = market?.question || question || 'Will this bill become law before this Congress ends?';

  async function choose(optionKey: string) {
    setSaving(true);
    setNotice('');
    try {
      const result = billId
        ? await setBillForecast(billId, optionKey)
        : await setElectionForecast(contestToken || '', optionKey);
      setMarket(result);
      setNotice('Forecast saved. You can change it until this forecast closes.');
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      setNotice(/401|authentication required/i.test(message) ? 'Sign in to save your forecast.' : (message || 'Forecast could not be saved.'));
    } finally {
      setSaving(false);
    }
  }

  if (!billId && !contestToken) return null;

  return (
    <section className={`rounded-2xl border border-[#214f78]/25 bg-sky-50 ${compact ? 'p-4' : 'p-5 sm:p-6'}`} aria-label="Civic forecast">
      <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.16em] text-[#214f78]"><BarChart3 className="h-4 w-4" />Community forecast</p>
      <h2 className={`${compact ? 'mt-2 text-base' : 'mt-3 text-xl'} font-black text-slate-950`}>{forecastQuestion}</h2>
      <p className="mt-2 text-xs leading-5 text-slate-600">Make a prediction for civic learning. No money, purchases, prizes, payouts, or transferable points.</p>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {visibleOptions.map((option) => {
          const selected = market?.current_user_choice === option.key;
          return <button key={option.key} type="button" disabled={saving || market?.status === 'resolved' || market?.status === 'locked'} onClick={() => choose(option.key)} className={`min-h-11 rounded-xl border px-4 text-left text-sm font-bold transition ${selected ? 'border-[#214f78] bg-[#214f78] text-white' : 'border-slate-300 bg-white text-slate-900 hover:border-[#214f78]'}`}>
            <span className="flex items-center justify-between gap-2"><span>{option.label}{option.party ? ` · ${option.party}` : ''}</span>{selected && <CheckCircle2 className="h-4 w-4" />}</span>
            {option.share != null && <span className={`mt-1 block text-xs ${selected ? 'text-sky-100' : 'text-slate-500'}`}>{option.share}% of published responses</span>}
          </button>;
        })}
      </div>
      {market && market.response_count == null && <p className="mt-3 text-xs text-slate-500">Totals appear after {market.privacy_threshold} participants to reduce exposure of individual choices.</p>}
      {notice && <p role="status" className="mt-3 text-sm text-slate-700">{notice} {notice.startsWith('Sign in') && <Link className="font-bold text-[#174f80] underline" to={`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`}>Sign in</Link>}</p>}
      {market?.resolution_source_url && <a className="mt-3 inline-block text-sm font-bold text-[#174f80] underline" href={market.resolution_source_url} target="_blank" rel="noreferrer">Official resolution source</a>}
    </section>
  );
}
