import { Users, Vote } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';

export default function ActHubPage() {
  const [searchParams] = useSearchParams();
  const targetType = searchParams.get('target_type') || '';
  const targetId = searchParams.get('target_id') || '';
  const representativesFrame = useRef<HTMLIFrameElement | null>(null);
  const [sharedZip, setSharedZip] = useState('');

  useEffect(() => {
    const receiveZip = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.data?.type !== 'wtp:act-zip') return;
      const zip = String(event.data.zip || '').replace(/\D/g, '').slice(0, 5);
      if (zip.length !== 5) return;
      setSharedZip(zip);
      representativesFrame.current?.contentWindow?.postMessage({ type: 'wtp:act-zip', zip }, window.location.origin);
    };
    window.addEventListener('message', receiveZip);
    return () => window.removeEventListener('message', receiveZip);
  }, []);

  return <main className="min-h-screen bg-[#080f1c] px-3 pb-32 pt-4 text-white sm:px-8 sm:py-12">
    <div className="mx-auto max-w-6xl">
      <header className="rounded-2xl bg-[#153d7a] px-4 py-4 shadow-lg shadow-black/20 sm:px-7 sm:py-6">
        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-blue-100">Civic Conversation Loop</p>
        <h1 className="mt-1 text-3xl font-black sm:text-5xl">ACT</h1>
        <p className="mt-2 max-w-3xl text-sm leading-5 text-blue-50 sm:text-lg sm:leading-7">Make your voice count. Plan your vote, then contact your representatives—two clear steps to turn concern into action. You stay in control; nothing is sent without your say.</p>
      </header>
      {targetType && targetId && <p className="mt-4 inline-flex rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-sm text-amber-100">ACT context: {targetType} · {targetId}</p>}
      <div aria-label="ACT options" className="mt-5 space-y-8">
        <section aria-labelledby="act-option-vote" className="overflow-hidden rounded-2xl border border-amber-300/40 bg-white shadow-xl shadow-black/20">
          <div className="flex items-center gap-4 bg-amber-300 p-4 text-slate-950 sm:p-5"><span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-slate-950 text-xl font-black text-amber-300" aria-hidden="true">1</span><div><p className="text-xs font-black uppercase tracking-[0.18em] text-slate-700">Step 1 · Voting</p><h2 id="act-option-vote" className="text-xl font-black sm:text-2xl">Plan my vote</h2><p className="mt-1 text-sm text-slate-800">See what is on your ballot and find where to vote.</p></div><Vote className="ml-auto hidden h-7 w-7 sm:block" aria-hidden="true" /></div>
          <iframe title="Step 1: Plan my vote" src="/elections?embed=1" className="h-[760px] w-full bg-[#eef1f5] sm:h-[820px]" loading="eager" />
        </section>
        <section aria-labelledby="act-option-reps" className="overflow-hidden rounded-2xl border border-white/15 bg-white shadow-xl shadow-black/20">
          <div className="flex items-center gap-4 bg-[#182231] p-4 text-white sm:p-5"><span className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-amber-300 text-xl font-black text-slate-950" aria-hidden="true">2</span><div><p className="text-xs font-black uppercase tracking-[0.18em] text-amber-300">Step 2 · Representation</p><h2 id="act-option-reps" className="text-xl font-black sm:text-2xl">Contact my representatives</h2><p className="mt-1 text-sm text-slate-300">Find who represents you and choose how to contact them.</p></div><Users className="ml-auto hidden h-7 w-7 text-amber-300 sm:block" aria-hidden="true" /></div>
          <iframe ref={representativesFrame} title="Step 2: Contact my representatives" src="/politics/find-rep?embed=1" onLoad={() => { if (sharedZip) representativesFrame.current?.contentWindow?.postMessage({ type: 'wtp:act-zip', zip: sharedZip }, window.location.origin); }} className="h-[760px] w-full bg-[#0b111b] sm:h-[820px]" loading="lazy" />
        </section>
      </div>
    </div>
  </main>;
}
