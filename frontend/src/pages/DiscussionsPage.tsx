import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { createDiscussion, fetchDiscussionContinuation, fetchPublicDiscussions, suggestDiscussionIssue, type DiscussionContinuation, type PublicDiscussionPost } from '../api/civic';
import { fetchIssueAgenda, type AgendaIssue } from '../api/issues';
import DiscussionPostCard from '../components/DiscussionPostCard';
import DiscussionVideoEmbed from '../components/DiscussionVideoEmbed';
import { useAuth } from '../contexts/AuthContext';

const PAGE_SIZE = 20;

function isSupportedSocialLink(value: string) {
  try {
    const hostname = new URL(value).hostname.toLowerCase().replace(/^www\./, '');
    return hostname === 'youtu.be' || hostname === 'youtube.com' || hostname.endsWith('.youtube.com')
      || hostname === 'tiktok.com' || hostname.endsWith('.tiktok.com')
      || hostname === 'instagram.com' || hostname.endsWith('.instagram.com')
      || hostname === 'facebook.com' || hostname.endsWith('.facebook.com')
      || hostname === 'fb.watch';
  } catch {
    return false;
  }
}

function supportedSocialLinkIn(value: string) {
  const candidate = value.match(/https:\/\/[^\s]+/)?.[0]?.replace(/[),.;!?]+$/, '') || '';
  return isSupportedSocialLink(candidate) ? candidate : '';
}

export default function DiscussionsPage() {
  const [params] = useSearchParams();
  const issue = params.get('issue') || '';
  const videoId = params.get('video') || '';
  const compose = params.get('compose') === '1';
  const composer = useRef<HTMLElement>(null);
  const [composerOpen, setComposerOpen] = useState(compose);
  const [items, setItems] = useState<PublicDiscussionPost[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [continuation, setContinuation] = useState<DiscussionContinuation | null>(null);
  const [continuationLoading, setContinuationLoading] = useState(false);
  const [continuationError, setContinuationError] = useState('');
  const [error, setError] = useState('');
  const [body, setBody] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [showLink, setShowLink] = useState(false);
  const [agendaIssues, setAgendaIssues] = useState<AgendaIssue[]>([]);
  const [selectedIssue, setSelectedIssue] = useState(issue);
  const [suggestionState, setSuggestionState] = useState<'idle' | 'loading' | 'ready' | 'unmatched' | 'error'>('idle');
  const [suggestedTitle, setSuggestedTitle] = useState('');
  const [showIssuePicker, setShowIssuePicker] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState('');
  const { isAuthenticated } = useAuth();
  const hasDemoItems = items.some((item) => item.author?.is_demo);
  const socialCandidate = videoUrl.trim() || supportedSocialLinkIn(body);

  useEffect(() => setSelectedIssue(issue), [issue]);

  useEffect(() => {
    if (issue || !socialCandidate || !isSupportedSocialLink(socialCandidate)) {
      setSuggestionState('idle');
      setSuggestedTitle('');
      setShowIssuePicker(false);
      if (!issue) setSelectedIssue('');
      return;
    }
    let active = true;
    const timeout = window.setTimeout(() => {
      setSuggestionState('loading');
      setShowIssuePicker(false);
      suggestDiscussionIssue(socialCandidate)
        .then((result) => {
          if (!active) return;
          if (result.suggested_issue) {
            setSelectedIssue(result.suggested_issue.slug);
            setSuggestedTitle(result.suggested_issue.title);
            setSuggestionState('ready');
          } else {
            setSelectedIssue('');
            setSuggestedTitle('');
            setSuggestionState('unmatched');
            setShowIssuePicker(true);
          }
        })
        .catch(() => {
          if (!active) return;
          setSelectedIssue('');
          setSuggestedTitle('');
          setSuggestionState('error');
          setShowIssuePicker(true);
        });
    }, 500);
    return () => { active = false; window.clearTimeout(timeout); };
  }, [issue, socialCandidate]);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setItems([]);
    fetchPublicDiscussions(issue || undefined, videoId || undefined, 0, PAGE_SIZE)
      .then((result) => { if (active) { setItems(result.items); setTotal(result.total); } })
      .catch((reason) => active && setError(reason instanceof Error ? reason.message : 'Discussions could not load.'))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [issue, videoId]);

  useEffect(() => {
    let active = true;
    fetchIssueAgenda()
      .then((agenda) => active && setAgendaIssues(Array.isArray(agenda.items) ? agenda.items : []))
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!composerOpen) return;
    if (typeof composer.current?.scrollIntoView === 'function') composer.current.scrollIntoView({ block: 'start' });
    composer.current?.querySelector<HTMLTextAreaElement>('textarea')?.focus();
  }, [composerOpen, isAuthenticated]);

  const loadMore = async () => {
    setLoadingMore(true); setError('');
    try {
      const result = await fetchPublicDiscussions(issue || undefined, videoId || undefined, items.length, PAGE_SIZE);
      setItems((current) => [...current, ...result.items]); setTotal(result.total);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'More discussions could not load.'); }
    finally { setLoadingMore(false); }
  };

  const loadContinuation = async () => {
    if (continuationLoading || continuation) return;
    setContinuationLoading(true); setContinuationError('');
    try {
      const result = await fetchDiscussionContinuation();
      setContinuation({
        reviewed_videos: result.reviewed_videos || [], agenda: result.agenda || [],
        bills: result.bills || [], bill_total: result.bill_total || 0,
      });
    }
    catch (reason) { setContinuationError(reason instanceof Error ? reason.message : 'More civic material could not load.'); }
    finally { setContinuationLoading(false); }
  };

  useEffect(() => {
    if (!loading && !error && !issue && !videoId && total > 0 && items.length >= total) void loadContinuation();
  }, [error, issue, items.length, loading, total, videoId]);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setNotice(''); setSubmitting(true);
    try {
      const trimmedLink = videoUrl.trim();
      const socialLink = trimmedLink && isSupportedSocialLink(trimmedLink) ? trimmedLink : supportedSocialLinkIn(body);
      const note = socialLink ? body.replace(socialLink, '').trim() : body.trim();
      const postBody = socialLink || !trimmedLink ? note : [note, trimmedLink].filter(Boolean).join('\n\n');
      if (postBody.length > 10000) throw new Error('Shorten your post before adding this link.');
      const result = await createDiscussion({ body: postBody, ...(socialLink ? { video_url: socialLink } : {}), ...(selectedIssue ? { issue_slug: selectedIssue } : {}) });
      setBody(''); setVideoUrl(''); setShowLink(false); setSelectedIssue(issue); setSuggestedTitle('');
      setNotice(result.moderation_status === 'published' ? 'Posted. It is now visible in Latest discussions.' : `${result.message}. It will appear here after review.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to submit post.'); }
    finally { setSubmitting(false); }
  };

  return <main className="min-h-screen bg-bg px-4 py-8 text-text-1 sm:px-6 sm:py-12">
    <div className="mx-auto max-w-6xl">
      <header className="border-b border-border pb-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">The civic feed</p>
        <h1 className="mt-2 font-display text-4xl sm:text-5xl">Discuss</h1>
        <p className="mt-3 max-w-3xl text-lg leading-7 text-text-2">Share and explore civic videos, links, ideas, and conversations—automatically organized around the People's Agenda.</p>
        <nav aria-label="Discussion feed views" className="mt-6 flex gap-2"><span aria-current="page" className="rounded-full bg-accent px-5 py-2.5 text-sm font-bold text-white">Latest</span><span className="rounded-full border border-border px-5 py-2.5 text-sm text-text-3" title="Following will be enabled after its privacy and notification contracts are complete">Following — later</span></nav>
        {videoId && <div className="mt-5 rounded-xl border border-accent/30 bg-accent/5 p-4"><p className="text-sm text-text-2">Showing the conversation connected to this video.</p><Link className="mt-2 inline-block font-semibold text-accent-text underline" to="/discuss">Return to the full feed</Link></div>}
        {issue && <div className="mt-5 rounded-xl border border-accent/30 bg-accent/5 p-4"><p className="text-sm text-text-2">Showing conversation connected to this issue's reviewed civic record.</p><Link className="mt-2 inline-block font-semibold text-accent-text underline" to={`/issues/${issue}`}>Return to official issue evidence</Link></div>}
      </header>

      <div className="mt-7 grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0">
          {!composerOpen ? <section ref={composer} id="composer" className="scroll-mt-20 rounded-2xl border border-border bg-surface p-3 sm:p-4" aria-label="Create a civic post">
            <div className="flex items-center gap-3"><div aria-hidden="true" className="grid h-11 w-11 shrink-0 place-content-center rounded-full bg-accent/15 font-bold text-accent-text">You</div><button type="button" onClick={() => setComposerOpen(true)} className="min-h-12 flex-1 rounded-full bg-bg px-5 text-left text-text-2 outline-none hover:bg-border/40 focus-visible:ring-4 focus-visible:ring-accent/30">What do you want people to know?</button></div>
            <div className="mt-3 grid grid-cols-3 border-t border-border pt-2 text-sm font-semibold"><button type="button" onClick={() => { setComposerOpen(true); setShowLink(true); }} className="min-h-11 rounded-lg text-accent-text hover:bg-bg">Video link</button><button type="button" onClick={() => { setComposerOpen(true); setShowLink(true); }} className="min-h-11 rounded-lg text-accent-text hover:bg-bg">Add link</button><button type="button" disabled title="In-app recording is coming later" className="min-h-11 rounded-lg text-text-3 opacity-60">Record later</button></div>
          </section> : <section ref={composer} id="composer" className="scroll-mt-20 rounded-2xl border border-border bg-surface p-5 sm:p-6" aria-labelledby="share-video-heading">
            <h2 id="share-video-heading" className="text-xl font-semibold">Share with your community</h2>
            <p className="mt-2 text-sm leading-6 text-text-2">Write a post, share a link, or do both.</p>
            {isAuthenticated ? <form className="mt-5 space-y-4" onSubmit={submit}>
              <label className="block text-sm font-semibold">What do you want people to know?<textarea className="mt-2 min-h-28 w-full rounded-xl border border-border bg-bg px-4 py-3 text-base leading-6 text-text-1" maxLength={10000} placeholder="Share a thought, question, or update…" value={body} onChange={(event) => setBody(event.target.value)} /></label>
              {showLink && <label className="block text-sm font-semibold">Link <span className="font-normal text-text-3">(optional)</span><input autoFocus className="mt-2 min-h-12 w-full rounded-xl border border-border bg-bg px-4 py-3 text-text-1" type="url" inputMode="url" pattern="https://.*" placeholder="https://…" value={videoUrl} onChange={(event) => setVideoUrl(event.target.value)} /><span className="mt-2 block text-xs font-normal leading-5 text-text-3">Web links open safely in a new tab. TikTok, Instagram, Facebook, and YouTube links are organized automatically.</span></label>}
              {socialCandidate && isSupportedSocialLink(socialCandidate) && !issue && <div aria-live="polite" className="rounded-xl border border-border bg-bg p-4">
                {suggestionState === 'loading' && <p className="text-sm text-text-2">Matching this video automatically…</p>}
                {suggestionState === 'ready' && <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-text-3">Suggested issue</p><p className="mt-1 font-semibold text-text-1">{suggestedTitle}</p></div><button type="button" className="font-semibold text-accent-text underline" onClick={() => setShowIssuePicker((current) => !current)}>{showIssuePicker ? 'Keep suggestion' : 'Change'}</button></div>}
                {suggestionState === 'unmatched' && <p className="text-sm text-text-2">Add a few words about the topic so we can match it.</p>}
                {suggestionState === 'error' && <p className="text-sm text-text-2">We will match the topic when you post.</p>}
              </div>}
              {(Boolean(issue) || showIssuePicker) && <label className="block text-sm font-semibold">Agenda issue<select className="mt-2 min-h-11 w-full rounded-xl border border-border bg-bg px-4 py-3 text-text-1" value={selectedIssue} onChange={(event) => { setSelectedIssue(event.target.value); setSuggestedTitle(agendaIssues.find((item) => item.slug === event.target.value)?.title || ''); setSuggestionState(event.target.value ? 'ready' : 'unmatched'); }} required disabled={Boolean(issue)}><option value="">Choose an issue</option>{agendaIssues.map((agendaIssue) => <option key={agendaIssue.slug} value={agendaIssue.slug}>{agendaIssue.title}</option>)}</select></label>}
              <div className="flex flex-wrap items-center gap-4">
                <button disabled={submitting || (!body.trim() && !videoUrl.trim())} className="min-h-12 rounded-full bg-accent px-7 py-3 font-bold text-white disabled:opacity-40">{submitting ? 'Posting…' : 'Post'}</button>
                {!showLink ? <button type="button" className="min-h-11 rounded-full border border-border px-4 text-sm font-semibold text-text-1 hover:bg-bg" onClick={() => setShowLink(true)}>Add link</button> : <button type="button" className="text-sm font-semibold text-text-2 underline" onClick={() => { setVideoUrl(''); setShowLink(false); }}>Remove link</button>}
              </div>
              <p className="text-xs leading-5 text-text-3">Signed-in posts appear immediately. Provider links are organized into the civic feed automatically.</p>
            </form> : <p className="mt-4"><Link className="font-semibold text-accent-text underline" to={`/login?next=${encodeURIComponent(compose ? '/discuss?compose=1#composer' : '/discuss')}`}>Sign in to start a conversation</Link></p>}
            {notice && <p role="status" className="mt-4 text-sm text-accent-text">{notice}</p>}
          </section>}

          {loading && <div className="mt-6 space-y-4" aria-label="Loading latest discussions"><div className="h-56 animate-pulse rounded-2xl border border-border bg-surface" /><div className="h-56 animate-pulse rounded-2xl border border-border bg-surface" /></div>}
          {error && <div role="alert" className="mt-6 rounded-2xl border border-red-300 bg-red-50 p-5 text-red-800">{error}<button type="button" onClick={() => window.location.reload()} className="ml-3 font-bold underline">Try again</button></div>}
          {!loading && !error && items.length === 0 && <div className="mt-6 rounded-2xl border border-dashed border-border bg-surface p-8 text-center"><h2 className="text-xl font-semibold">No posts here yet</h2><p className="mt-2 text-text-2">{videoId ? 'No published conversation is connected to this video yet.' : 'Be the first to share a civic thought, link, or video.'}</p><Link className="mt-5 inline-block font-semibold text-accent-text underline" to="/discuss?compose=1#composer">Create a post</Link></div>}

          {!loading && !error && items.length > 0 && <div className="mt-6 flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-text">Newest first</p><h2 className="mt-1 text-2xl font-semibold">{videoId ? 'Video conversation' : issue ? 'Issue conversation' : 'Latest discussions'}</h2></div><p className="shrink-0 text-sm text-text-3">{total} {total === 1 ? 'thread' : 'threads'}</p></div>}
          {!loading && !error && hasDemoItems && <aside role="note" className="mt-4 rounded-xl border border-amber-500/40 bg-amber-300/10 p-4 text-sm leading-6 text-text-2"><strong className="text-text-1">Visual demo:</strong> Latin placeholder posts, numbered test users, replies, and reactions are shown here to test the civic feed. They are not real civic participation.</aside>}
          <section aria-label="Latest civic discussions" className="mt-4 space-y-4 sm:space-y-5">{items.map((item) => <DiscussionPostCard key={item.id} item={item} isAuthenticated={isAuthenticated} />)}</section>
          {items.length < total && <div className="mt-6 text-center"><button type="button" disabled={loadingMore} onClick={() => void loadMore()} className="min-h-11 rounded-full border border-border bg-surface px-6 font-bold text-text-1 disabled:opacity-60">{loadingMore ? 'Loading…' : `Load more (${total - items.length} remaining)`}</button></div>}
          {!issue && !videoId && continuationLoading && <p className="mt-8 text-center text-sm text-text-2">Loading more real civic material…</p>}
          {!issue && !videoId && continuationError && <div role="alert" className="mt-8 rounded-xl border border-border bg-surface p-5 text-center"><p>{continuationError} Your loaded posts remain available.</p><button className="mt-3 font-bold text-accent-text underline" onClick={() => void loadContinuation()}>Try again</button></div>}
          {continuation && <section className="mt-10 space-y-5" aria-label="More civic material">
            <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-accent-text">Continue exploring</p><h2 className="mt-1 text-2xl font-semibold">Reviewed videos and civic context</h2></div>
            {continuation.reviewed_videos.map((video) => <article key={`video:${video.video_id}`} className="rounded-2xl border border-border bg-surface p-5 sm:p-6"><p className="text-xs font-bold uppercase tracking-[0.14em] text-accent-text">Reviewed video · {video.issue.title}</p><h3 className="mt-2 text-xl font-semibold">{video.caption}</h3><p className="mt-1 text-sm text-text-3">{video.creator_label} · Source: {video.source.publisher}</p>{video.delivery?.provider && video.delivery.provider_video_id ? <DiscussionVideoEmbed title={video.caption} video={{ provider: video.delivery.provider as 'youtube' | 'tiktok' | 'facebook' | 'instagram', provider_video_id: video.delivery.provider_video_id, canonical_url: video.delivery.canonical_url }} /> : <a className="mt-4 inline-block font-semibold text-accent-text underline" href={video.source.url} target="_blank" rel="noreferrer">Open the reviewed source</a>}<div className="mt-4 flex gap-4"><Link className="font-semibold text-accent-text underline" to={`/issues/${video.issue.slug}`}>Explore {video.issue.title}</Link><Link className="font-semibold text-accent-text underline" to={`/discuss?video=${encodeURIComponent(video.video_id)}`}>Conversation</Link></div></article>)}
            {continuation.agenda.map((item) => <article key={`agenda:${item.slug}`} className="rounded-2xl border border-border bg-surface p-5 sm:p-6"><p className="text-xs font-bold uppercase tracking-[0.14em] text-accent-text">People's Agenda</p><h3 className="mt-2 text-xl font-semibold">{item.title}</h3>{item.summary && <p className="mt-2 leading-7 text-text-2">{item.summary}</p>}<p className="mt-3 text-sm text-text-3">{item.priority_note} · {item.bill_count} linked bills</p><Link className="mt-4 inline-block font-semibold text-accent-text underline" to={`/issues/${item.slug}`}>Explore this issue</Link></article>)}
            {continuation.bills.map((bill) => <article key={`bill:${bill.bill_id}`} className="rounded-2xl border border-border bg-surface p-5 sm:p-6"><p className="text-xs font-bold uppercase tracking-[0.14em] text-accent-text">Current legislation</p><h3 className="mt-2 text-xl font-semibold">{bill.title || bill.bill_id.toUpperCase()}</h3>{bill.latest_action_text && <p className="mt-2 leading-7 text-text-2">{bill.latest_action_text}</p>}<Link className="mt-4 inline-block font-semibold text-accent-text underline" to={`/politics/bill/${bill.bill_id}`}>Read the bill record</Link></article>)}
          </section>}
        </div>

        <aside className="rounded-2xl border border-border bg-surface p-5 lg:sticky lg:top-6" aria-label="About this feed"><h2 className="font-semibold">How this feed works</h2><ul className="mt-3 space-y-3 text-sm leading-6 text-text-2"><li>Newest published posts appear first.</li><li>Videos play here after provider consent.</li><li>Agenda labels connect posts to civic context and evidence.</li><li>Bookmarks are private. Reactions show totals, never participant lists.</li><li>Reports go privately to moderation.</li></ul></aside>
      </div>
    </div>
  </main>;
}
