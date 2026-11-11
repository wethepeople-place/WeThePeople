import { ArrowDown, ArrowRight, Users, Vote } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';

function StepDirection({ number, label }: { number: string; label: string }) {
  return <div aria-hidden="true" className="pointer-events-none absolute -left-32 top-7 hidden w-28 items-center justify-end gap-3 xl:flex">
    <div className="text-right">
      <p className="text-[9px] font-bold uppercase tracking-[0.22em] text-slate-600">Step {number}</p>
      <p className="mt-1 text-xs font-semibold text-slate-400">{label}</p>
    </div>
    <ArrowRight className="h-6 w-6 shrink-0 text-slate-500" strokeWidth={1.75} />
  </div>;
}

export default function ActHubPage() {
  const [searchParams] = useSearchParams();
  const targetType = searchParams.get('target_type') || '';
  const targetId = searchParams.get('target_id') || '';
  const electionsFrame = useRef<HTMLIFrameElement | null>(null);
  const representativesFrame = useRef<HTMLIFrameElement | null>(null);
  const [sharedZip, setSharedZip] = useState('');
  const [frameHeights, setFrameHeights] = useState({ elections: 560, representatives: 520 });

  useEffect(() => {
    const receiveZip = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type === 'wtp:act-frame-height') {
        const frame = event.data.frame === 'elections' ? 'elections' : event.data.frame === 'representatives' ? 'representatives' : null;
        if (!frame) return;
        const expectedSource = frame === 'elections' ? electionsFrame.current?.contentWindow : representativesFrame.current?.contentWindow;
        if (event.source !== expectedSource) return;
        const height = Math.max(320, Math.min(5000, Math.ceil(Number(event.data.height) || 0)));
        setFrameHeights((current) => current[frame] === height ? current : { ...current, [frame]: height });
        return;
      }
      if (event.data?.type === 'wtp:act-zip') {
        const zip = String(event.data.zip || '').replace(/\D/g, '').slice(0, 5);
        if (zip.length !== 5) return;
        setSharedZip(zip);
        representativesFrame.current?.contentWindow?.postMessage({ type: 'wtp:act-zip', zip }, window.location.origin);
      }
    };
    window.addEventListener('message', receiveZip);
    return () => window.removeEventListener('message', receiveZip);
  }, []);

  return <main className="relative min-h-screen overflow-hidden bg-[#0b0c0f] px-3 pb-32 pt-4 text-white sm:px-8 sm:py-12">
    <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(circle_at_18%_0%,rgba(164,174,190,0.08),transparent_44%),radial-gradient(circle_at_88%_12%,rgba(255,255,255,0.035),transparent_35%)]" />
    <div className="relative mx-auto max-w-6xl">
      <header className="rounded-[28px] border border-white/[0.07] bg-[#14161a]/90 px-5 py-6 shadow-2xl shadow-black/20 backdrop-blur-xl sm:px-10 sm:py-10">
        <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1fr)_250px] lg:gap-10">
          <div>
            <div className="flex items-center gap-3"><span className="h-2 w-2 rounded-full bg-slate-400 shadow-[0_0_14px_rgba(180,190,205,0.35)]" /><p className="text-[11px] font-bold uppercase tracking-[0.22em] text-slate-500">Civic action</p></div>
            <h1 className="mt-5 text-sm font-semibold tracking-wide text-slate-400">ACT</h1>
            <p className="mt-2 text-3xl font-semibold leading-[1.08] tracking-[-0.035em] text-slate-100 sm:text-5xl xl:text-6xl">Don’t like what those old men decide? <span className="bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">Change who gets to decide.</span></p>
            <p className="mt-5 max-w-3xl text-lg font-medium leading-7 text-slate-200 sm:text-2xl sm:leading-8">If their agenda doesn’t align with yours, vote them out.</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400 sm:text-base sm:leading-7">Plan your vote. Contact your representatives. Make your voice count. You stay in control; nothing is sent without your say.</p>
          </div>

          <figure className="mx-auto w-full max-w-[250px] rounded-[26px] border border-white/10 bg-white/[0.025] p-2 shadow-2xl shadow-black/30 lg:justify-self-end">
            <div className="aspect-[9/14] overflow-hidden rounded-[20px] bg-[#0d0f13]">
              <img
                src="/images/act-dan-patrick-thc-june-2025.png"
                alt="Texas Lieutenant Governor Dan Patrick speaking at a podium in a June 2025 Fox 4 clip about his THC policy position"
                className="h-full w-full object-cover object-center saturate-[0.82] contrast-[0.96]"
                fetchPriority="high"
              />
            </div>
            <figcaption className="px-2 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">Policy debate · Texas · June 2025</figcaption>
          </figure>
        </div>
      </header>
      <div aria-label="ACT options" className="mt-6 sm:mt-8">
        <nav aria-label="Your two-step action path" className="mb-7 rounded-[26px] border border-white/10 bg-[#121419] p-4 shadow-xl shadow-black/20 sm:p-6">
          <div className="mb-4 sm:mb-5">
            <h2 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">Choose what you want to do</h2>
            <p className="mt-1 text-base leading-6 text-slate-300">Pick a step below. We’ll guide you from there.</p>
            {targetType && targetId && <p className="mt-2 text-sm font-medium text-slate-400">You came here ready to act—start with either option.</p>}
          </div>
          <div className="grid items-stretch gap-3 md:grid-cols-[1fr_auto_1fr] md:gap-4">
            <a href="#act-option-vote" className="group flex min-h-28 items-center gap-4 rounded-2xl border border-[#7195c9]/55 bg-[#1b2d44] px-5 py-4 outline-none transition hover:border-[#91b4e5]/80 hover:bg-[#213750] focus-visible:ring-4 focus-visible:ring-[#7195c9]/30">
              <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-[#9dbce7] text-xl font-black text-[#101d2c] shadow-lg shadow-black/20">1</span>
              <span className="min-w-0"><span className="block text-xs font-bold uppercase tracking-[0.18em] text-[#abc7ed]">Start here</span><span className="mt-1 block text-xl font-bold text-white">Plan my vote</span><span className="mt-1 block text-sm leading-5 text-[#c4d2e5]">See your ballot and polling place</span></span>
            </a>
            <div className="hidden items-center justify-center md:flex"><ArrowRight className="h-7 w-7 text-slate-500" strokeWidth={2} aria-hidden="true" /></div>
            <a href="#act-option-reps" className="group flex min-h-28 items-center gap-4 rounded-2xl border border-[#9584bd]/55 bg-[#302a43] px-5 py-4 outline-none transition hover:border-[#b2a2d9]/80 hover:bg-[#39314e] focus-visible:ring-4 focus-visible:ring-[#9584bd]/30">
              <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-[#afa0d4] text-xl font-black text-[#211c30] shadow-lg shadow-black/20">2</span>
              <span className="min-w-0"><span className="block text-xs font-bold uppercase tracking-[0.18em] text-[#c5b9e3]">Or go here</span><span className="mt-1 block text-xl font-bold text-white">Contact my representatives</span><span className="mt-1 block text-sm leading-5 text-[#d1cae1]">Find, review, and contact your officials</span></span>
            </a>
          </div>
        </nav>

        <div className="relative">
          <StepDirection number="1" label="Start here" />
          <section aria-labelledby="act-option-vote" className="overflow-hidden rounded-[28px] border border-white/[0.07] bg-[#121418] shadow-2xl shadow-black/20">
            <div className="flex items-center gap-4 border-b border-[#7195c9]/35 border-l-4 border-l-[#8fb2e1] bg-[#182638] p-5 text-white sm:p-7"><span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-[#9dbce7] text-xl font-black text-[#101d2c] shadow-lg shadow-black/20" aria-hidden="true">1</span><div><p className="text-xs font-bold uppercase tracking-[0.2em] text-[#abc7ed]">Step 1 of 2 · Voting</p><h2 id="act-option-vote" className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">Plan my vote</h2><p className="mt-1 text-base leading-6 text-[#c4d2e5]">Choose your state below. We’ll guide you through the rest.</p></div><Vote className="ml-auto hidden h-7 w-7 text-[#9dbce7] sm:block" aria-hidden="true" /></div>
            <iframe ref={electionsFrame} title="Step 1: Plan my vote" src="/elections?embed=1" style={{ height: frameHeights.elections }} className="block w-full border-0 bg-[#eef1f5]" loading="eager" />
          </section>
        </div>

        <div className="relative flex h-24 items-center justify-center" aria-label="Continue to step 2">
          <span aria-hidden="true" className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-gradient-to-b from-white/[0.04] via-slate-500/45 to-white/[0.04]" />
          <a
            href="#act-option-reps"
            className="group relative inline-flex min-h-11 items-center gap-2 rounded-full border border-white/10 bg-[#15171c]/95 px-4 text-xs font-semibold tracking-wide text-slate-300 shadow-xl shadow-black/20 backdrop-blur-xl transition hover:border-white/20 hover:bg-[#1b1e24] hover:text-slate-100 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-slate-400/15"
          >
            <span className="hidden sm:inline">Next: contact your representatives</span>
            <span className="sm:hidden">Continue to step 2</span>
            <ArrowDown className="h-4 w-4 text-slate-500 transition-transform group-hover:translate-y-0.5 group-hover:text-slate-300" aria-hidden="true" />
          </a>
        </div>

        <div className="relative">
          <StepDirection number="2" label="Next step" />
          <section aria-labelledby="act-option-reps" className="overflow-hidden rounded-[28px] border border-white/[0.07] bg-[#121418] shadow-2xl shadow-black/20">
            <div className="flex items-center gap-4 border-b border-[#9584bd]/35 border-l-4 border-l-[#aa9ace] bg-[#28243a] p-5 text-white sm:p-7"><span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-[#afa0d4] text-xl font-black text-[#211c30] shadow-lg shadow-black/20" aria-hidden="true">2</span><div><p className="text-xs font-bold uppercase tracking-[0.2em] text-[#c5b9e3]">Step 2 of 2 · Representation</p><h2 id="act-option-reps" className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">Contact my representatives</h2><p className="mt-1 text-base leading-6 text-[#d1cae1]">Enter your ZIP code, choose a representative, then decide how to contact them.</p></div><Users className="ml-auto hidden h-7 w-7 text-[#afa0d4] sm:block" aria-hidden="true" /></div>
            <iframe ref={representativesFrame} title="Step 2: Contact my representatives" src="/politics/find-rep?embed=1" onLoad={() => { if (sharedZip) representativesFrame.current?.contentWindow?.postMessage({ type: 'wtp:act-zip', zip: sharedZip }, window.location.origin); }} style={{ height: frameHeights.representatives }} className="block w-full border-0 bg-[#0b111b]" loading="lazy" />
          </section>
        </div>
      </div>
    </div>
  </main>;
}
