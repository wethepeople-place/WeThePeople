import { useEffect, useState } from 'react';
import { CalendarDays, ChevronRight, ExternalLink, Gavel, MapPin, ShieldCheck, Users, Vote } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

import {
  fetchActionCircles, fetchCivicActivities, joinActionCircle, rsvpCivicActivity,
  type PublicActionCircle, type PublicCivicActivity,
} from '../api/civic';
import { useAuth } from '../contexts/AuthContext';

export default function ActHubPage() {
  const [searchParams] = useSearchParams();
  const targetType = searchParams.get('target_type') || '';
  const targetId = searchParams.get('target_id') || '';
  const { isAuthenticated } = useAuth();
  const [circles, setCircles] = useState<PublicActionCircle[]>([]);
  const [activities, setActivities] = useState<PublicCivicActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    Promise.all([fetchActionCircles(targetType, targetId), fetchCivicActivities()])
      .then(([circleData, activityData]) => { setCircles(circleData.items); setActivities(activityData.items); })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'ACT opportunities could not load.'))
      .finally(() => setLoading(false));
  }, [targetId, targetType]);

  const join = async (circle: PublicActionCircle) => {
    setError('');
    try {
      const result = await joinActionCircle(circle.id);
      setNotice(result.status === 'active' ? `You joined ${circle.name}. Your identity remains private.` : `Your request to join ${circle.name} is pending.`);
      setCircles((current) => current.map((item) => item.id === circle.id ? { ...item, viewer_membership_status: result.status, member_count: item.member_count + (result.status === 'active' ? 1 : 0) } : item));
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The Circle could not be joined.'); }
  };

  const rsvp = async (activity: PublicCivicActivity) => {
    setError('');
    try { await rsvpCivicActivity(activity.id); setNotice(`Your RSVP for ${activity.title} is private.`); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'The RSVP could not be saved.'); }
  };

  return <main className="min-h-screen bg-[#080f1c] px-3 pb-32 pt-4 text-white sm:px-8 sm:py-12">
    <div className="mx-auto max-w-6xl">
      <header className="rounded-2xl bg-[#153d7a] px-4 py-4 shadow-lg shadow-black/20 sm:px-7 sm:py-6">
        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-blue-100">Civic Conversation Loop</p>
        <h1 className="mt-1 text-3xl font-black sm:text-5xl">ACT</h1>
        <p className="mt-2 max-w-3xl text-sm leading-5 text-blue-50 sm:text-lg sm:leading-7">Choose one concrete civic step. Nothing is sent, joined, signed, or submitted automatically.</p>
      </header>
      {targetType && targetId && <p className="mt-4 inline-flex rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-sm text-amber-100">ACT context: {targetType} · {targetId}</p>}
      <div aria-label="Choose an ACT destination" className="mt-3 grid grid-cols-2 gap-2.5 sm:mt-5 sm:gap-4 lg:grid-cols-4">
        <Link to="/elections" className="group flex min-h-40 flex-col rounded-2xl bg-amber-300 p-4 text-slate-950 outline-none transition hover:bg-amber-200 focus-visible:ring-4 focus-visible:ring-white/70 sm:min-h-48 sm:p-5"><Vote className="h-6 w-6" /><h2 className="mt-3 text-lg font-black sm:text-xl">Elections</h2><p className="mt-1 text-sm leading-5 text-slate-800">Plan your vote with official ballot and location information.</p><ChevronRight className="mt-auto h-5 w-5 self-end transition group-hover:translate-x-0.5" aria-hidden="true" /></Link>
        <Link to="/politics/find-rep" className="group flex min-h-40 flex-col rounded-2xl border border-white/15 bg-white/[.07] p-4 outline-none transition hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-amber-300/60 sm:min-h-48 sm:p-5"><Users className="h-6 w-6 text-amber-300" /><h2 className="mt-3 text-lg font-black sm:text-xl">Representatives</h2><p className="mt-1 text-sm leading-5 text-slate-300">Find and contact the public officials who represent you.</p><ChevronRight className="mt-auto h-5 w-5 self-end text-amber-300 transition group-hover:translate-x-0.5" aria-hidden="true" /></Link>
        <a href="#activities" className="group flex min-h-40 flex-col rounded-2xl border border-white/15 bg-white/[.07] p-4 outline-none transition hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-amber-300/60 sm:min-h-48 sm:p-5"><CalendarDays className="h-6 w-6 text-amber-300" /><h2 className="mt-3 text-lg font-black sm:text-xl">Activities</h2><p className="mt-1 text-sm leading-5 text-slate-300">Find moderated meetings, hearings, call days, and events.</p><ChevronRight className="mt-auto h-5 w-5 self-end text-amber-300 transition group-hover:translate-x-0.5" aria-hidden="true" /></a>
        <a href="#circles" className="group flex min-h-40 flex-col rounded-2xl border border-white/15 bg-white/[.07] p-4 outline-none transition hover:bg-white/10 focus-visible:ring-4 focus-visible:ring-amber-300/60 sm:min-h-48 sm:p-5"><ShieldCheck className="h-6 w-6 text-amber-300" /><h2 className="mt-3 text-lg font-black sm:text-xl">Action Circles</h2><p className="mt-1 text-sm leading-5 text-slate-300">Organize around a reviewed objective and completion goal.</p><ChevronRight className="mt-auto h-5 w-5 self-end text-amber-300 transition group-hover:translate-x-0.5" aria-hidden="true" /></a>
      </div>
      {loading && <p className="mt-10 text-slate-300">Loading moderated ACT opportunities…</p>}
      {error && <p role="alert" className="mt-8 rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-rose-200">{error}</p>}
      {notice && <p role="status" className="mt-8 rounded-xl border border-amber-300/30 bg-amber-300/10 p-4 text-amber-100">{notice}</p>}
      <section id="circles" className="mt-10 scroll-mt-4 sm:mt-14 sm:scroll-mt-6"><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-widest text-amber-300 sm:text-sm">Objective-based groups</p><h2 className="mt-1 text-2xl font-bold sm:text-3xl">Action Circles</h2></div><ShieldCheck className="h-7 w-7 text-slate-400" /></div>
        {!loading && circles.length === 0 && <div className="mt-5 rounded-2xl border border-dashed border-white/20 p-8 text-center"><h3 className="text-lg font-bold">No moderated Circles are public yet</h3><p className="mt-2 text-slate-400">New Circles appear only after their objective, evidence, conduct rules, and privacy settings are reviewed.</p></div>}
        <div className="mt-5 grid gap-4 md:grid-cols-2">{circles.map((circle) => <article key={circle.id} className="rounded-2xl border border-white/10 bg-white/5 p-5"><div className="flex flex-wrap gap-2 text-xs text-slate-300"><span className="rounded-full bg-white/10 px-2 py-1">{circle.target_type}: {circle.target_id}</span>{circle.geography && <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2 py-1"><MapPin className="h-3 w-3" />{circle.geography}</span>}</div><h3 className="mt-3 text-xl font-bold">{circle.name}</h3><p className="mt-2 leading-6 text-slate-300">{circle.objective}</p><p className="mt-3 text-sm text-slate-400">Completion: {circle.completion_condition}</p><div className="mt-4 flex items-center justify-between gap-3"><span className="text-sm text-slate-400">{circle.member_count} participating · identities private</span>{circle.viewer_membership_status ? <span className="font-bold text-amber-200">{circle.viewer_membership_status}</span> : isAuthenticated ? <button type="button" onClick={() => void join(circle)} className="min-h-11 rounded-full bg-amber-300 px-4 font-bold text-slate-950">{circle.membership_mode === 'open' ? 'Join Circle' : 'Request to join'}</button> : <Link to="/login?next=%2Fact" className="font-bold text-amber-300 underline">Sign in to join</Link>}</div></article>)}</div>
      </section>
      <section id="activities" className="mt-10 scroll-mt-4 sm:mt-14 sm:scroll-mt-6"><p className="text-xs font-bold uppercase tracking-widest text-amber-300 sm:text-sm">Moderated opportunities</p><h2 className="mt-1 text-2xl font-bold sm:text-3xl">Activities</h2>
        {!loading && activities.length === 0 && <div className="mt-5 rounded-2xl border border-dashed border-white/20 p-8 text-center"><h3 className="text-lg font-bold">No upcoming moderated activities</h3><p className="mt-2 text-slate-400">Unreviewed community submissions are never published automatically.</p></div>}
        <div className="mt-5 grid gap-4 md:grid-cols-2">{activities.map((activity) => <article key={activity.id} className="rounded-2xl border border-white/10 bg-white/5 p-5"><div className="text-xs font-bold uppercase tracking-widest text-amber-300">{activity.host_type} · {activity.format}</div><h3 className="mt-2 text-xl font-bold">{activity.title}</h3><p className="mt-2 leading-6 text-slate-300">{activity.description}</p><p className="mt-3 text-sm text-slate-400">{new Date(activity.starts_at).toLocaleString()} · {activity.timezone}</p><div className="mt-4 flex flex-wrap gap-3">{activity.public_url && <a href={activity.public_url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-white/20 px-4 font-bold"><ExternalLink className="h-4 w-4" />Official details</a>}{isAuthenticated ? <button type="button" onClick={() => void rsvp(activity)} className="min-h-11 rounded-full bg-amber-300 px-4 font-bold text-slate-950">RSVP privately</button> : <Link to="/login?next=%2Fact" className="self-center font-bold text-amber-300 underline">Sign in to RSVP</Link>}</div></article>)}</div>
      </section>
      <details className="mt-10 rounded-2xl border border-white/10 bg-white/[.04] p-4 text-slate-300 sm:mt-14 sm:p-6"><summary className="flex min-h-11 cursor-pointer list-none items-center gap-3 font-bold text-slate-200"><Gavel className="h-5 w-5 text-slate-400" />About future legal pathways</summary><p className="mt-3 max-w-3xl text-sm leading-6">Legal pathways are not enabled, and WTP will not offer a casual “Join lawsuit” button. Any future pathway must use verified court or administrator sources and pass a separate legal, privacy, and operator review. WTP will not decide eligibility or enroll plaintiffs.</p></details>
    </div>
  </main>;
}
