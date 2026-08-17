import { useEffect, useState } from 'react';
import { CalendarDays, ExternalLink, Gavel, MapPin, Megaphone, ShieldCheck, Users, Vote } from 'lucide-react';
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

  return <main className="min-h-screen bg-[#080f1c] px-4 py-12 text-white sm:px-8">
    <div className="mx-auto max-w-6xl">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-amber-300">Civic Conversation Loop</p>
      <h1 className="mt-2 text-4xl font-bold sm:text-5xl">ACT</h1>
      <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-300">Start with the civic action that matters most: know when, where, and what you can vote on. Nothing is sent, joined, signed, or submitted automatically.</p>
      {targetType && targetId && <p className="mt-4 inline-flex rounded-full border border-amber-300/30 bg-amber-300/10 px-4 py-2 text-sm text-amber-100">ACT context: {targetType} · {targetId}</p>}
      <Link to="/elections" className="mt-8 flex items-center justify-between gap-5 rounded-2xl bg-amber-300 p-5 text-slate-950 outline-none focus-visible:ring-4 focus-visible:ring-white/70"><div><p className="text-xs font-black uppercase tracking-widest">ACT first</p><h2 className="mt-1 text-2xl font-black">Plan your vote</h2><p className="mt-2 leading-6 text-slate-800">Find upcoming elections, your ballot, official voting locations, and registration links without saving your address.</p></div><Vote className="h-9 w-9 shrink-0" /></Link>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Link to="/politics/find-rep" className="rounded-2xl border border-white/10 bg-white/5 p-5 outline-none hover:bg-white/[.08] focus-visible:ring-4 focus-visible:ring-amber-300/60"><Megaphone className="h-6 w-6 text-amber-300" /><h2 className="mt-3 text-xl font-bold">Contact government</h2><p className="mt-2 leading-6 text-slate-300">Find the right representative, call a verified public office, or prepare an editable message.</p></Link>
        <a href="#circles" className="rounded-2xl border border-white/10 bg-white/5 p-5 outline-none hover:bg-white/[.08] focus-visible:ring-4 focus-visible:ring-amber-300/60"><Users className="h-6 w-6 text-amber-300" /><h2 className="mt-3 text-xl font-bold">Join an Action Circle</h2><p className="mt-2 leading-6 text-slate-300">Organize around one objective, jurisdiction, and completion condition.</p></a>
        <a href="#activities" className="rounded-2xl border border-white/10 bg-white/5 p-5 outline-none hover:bg-white/[.08] focus-visible:ring-4 focus-visible:ring-amber-300/60"><CalendarDays className="h-6 w-6 text-amber-300" /><h2 className="mt-3 text-xl font-bold">Participate</h2><p className="mt-2 leading-6 text-slate-300">Find moderated meetings, call days, hearings, and community activities.</p></a>
      </div>
      {loading && <p className="mt-10 text-slate-300">Loading moderated ACT opportunities…</p>}
      {error && <p role="alert" className="mt-8 rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-rose-200">{error}</p>}
      {notice && <p role="status" className="mt-8 rounded-xl border border-amber-300/30 bg-amber-300/10 p-4 text-amber-100">{notice}</p>}
      <section id="circles" className="mt-14 scroll-mt-6"><div className="flex items-end justify-between gap-4"><div><p className="text-sm font-bold uppercase tracking-widest text-amber-300">Objective-based groups</p><h2 className="mt-1 text-3xl font-bold">Action Circles</h2></div><ShieldCheck className="h-7 w-7 text-slate-400" /></div>
        {!loading && circles.length === 0 && <div className="mt-5 rounded-2xl border border-dashed border-white/20 p-8 text-center"><h3 className="text-lg font-bold">No moderated Circles are public yet</h3><p className="mt-2 text-slate-400">New Circles appear only after their objective, evidence, conduct rules, and privacy settings are reviewed.</p></div>}
        <div className="mt-5 grid gap-4 md:grid-cols-2">{circles.map((circle) => <article key={circle.id} className="rounded-2xl border border-white/10 bg-white/5 p-5"><div className="flex flex-wrap gap-2 text-xs text-slate-300"><span className="rounded-full bg-white/10 px-2 py-1">{circle.target_type}: {circle.target_id}</span>{circle.geography && <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2 py-1"><MapPin className="h-3 w-3" />{circle.geography}</span>}</div><h3 className="mt-3 text-xl font-bold">{circle.name}</h3><p className="mt-2 leading-6 text-slate-300">{circle.objective}</p><p className="mt-3 text-sm text-slate-400">Completion: {circle.completion_condition}</p><div className="mt-4 flex items-center justify-between gap-3"><span className="text-sm text-slate-400">{circle.member_count} participating · identities private</span>{circle.viewer_membership_status ? <span className="font-bold text-amber-200">{circle.viewer_membership_status}</span> : isAuthenticated ? <button type="button" onClick={() => void join(circle)} className="min-h-11 rounded-full bg-amber-300 px-4 font-bold text-slate-950">{circle.membership_mode === 'open' ? 'Join Circle' : 'Request to join'}</button> : <Link to="/login?next=%2Fact" className="font-bold text-amber-300 underline">Sign in to join</Link>}</div></article>)}</div>
      </section>
      <section id="activities" className="mt-14 scroll-mt-6"><p className="text-sm font-bold uppercase tracking-widest text-amber-300">Moderated opportunities</p><h2 className="mt-1 text-3xl font-bold">Activities</h2>
        {!loading && activities.length === 0 && <div className="mt-5 rounded-2xl border border-dashed border-white/20 p-8 text-center"><h3 className="text-lg font-bold">No upcoming moderated activities</h3><p className="mt-2 text-slate-400">Unreviewed community submissions are never published automatically.</p></div>}
        <div className="mt-5 grid gap-4 md:grid-cols-2">{activities.map((activity) => <article key={activity.id} className="rounded-2xl border border-white/10 bg-white/5 p-5"><div className="text-xs font-bold uppercase tracking-widest text-amber-300">{activity.host_type} · {activity.format}</div><h3 className="mt-2 text-xl font-bold">{activity.title}</h3><p className="mt-2 leading-6 text-slate-300">{activity.description}</p><p className="mt-3 text-sm text-slate-400">{new Date(activity.starts_at).toLocaleString()} · {activity.timezone}</p><div className="mt-4 flex flex-wrap gap-3">{activity.public_url && <a href={activity.public_url} target="_blank" rel="noreferrer" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-white/20 px-4 font-bold"><ExternalLink className="h-4 w-4" />Official details</a>}{isAuthenticated ? <button type="button" onClick={() => void rsvp(activity)} className="min-h-11 rounded-full bg-amber-300 px-4 font-bold text-slate-950">RSVP privately</button> : <Link to="/login?next=%2Fact" className="self-center font-bold text-amber-300 underline">Sign in to RSVP</Link>}</div></article>)}</div>
      </section>
      <section className="mt-14 rounded-2xl border border-white/10 bg-white/5 p-6"><Gavel className="h-6 w-6 text-slate-400" /><h2 className="mt-3 text-xl font-bold">Legal pathways are not enabled</h2><p className="mt-2 max-w-3xl leading-6 text-slate-300">WTP will not offer a casual “Join lawsuit” button. Any future legal pathway must use verified court or administrator sources and pass a separate legal, privacy, and operator review. WTP will not decide eligibility or enroll plaintiffs.</p></section>
    </div>
  </main>;
}
