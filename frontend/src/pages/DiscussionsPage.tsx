import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';

import { createCitizenSolution, createDiscussion, fetchPublicDiscussions, suggestDiscussionIssue, type CommunityView, type PublicDiscussionPost } from '../api/civic';
import DiscussionPostCard from '../components/DiscussionPostCard';
import DiscussionVideoEmbed from '../components/DiscussionVideoEmbed';
import { useAuth } from '../contexts/AuthContext';

const PAGE_SIZE = 20;
type DiscussionSort = 'recent' | 'popular' | 'discussed';

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
  const { pathname } = useLocation();
  const issue = params.get('issue') || '';
  const videoId = params.get('video') || '';
  const compose = params.get('compose') === '1' || params.get('compose') === 'proposal';
  const requestedView = params.get('view');
  const view: CommunityView = pathname === '/proposals' || requestedView === 'proposals' ? 'proposals' : 'discussions';
  const proposalsOnly = view === 'proposals';
  const composer = useRef<HTMLElement>(null);
  const [items, setItems] = useState<PublicDiscussionPost[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [body, setBody] = useState('');
  const [postKind, setPostKind] = useState<'discussion' | 'proposal'>(proposalsOnly || params.get('compose') === 'proposal' ? 'proposal' : 'discussion');
  const [selectedIssue, setSelectedIssue] = useState(issue);
  const [suggestionState, setSuggestionState] = useState<'idle' | 'loading' | 'ready' | 'unmatched' | 'error'>('idle');
  const [suggestedTitle, setSuggestedTitle] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState('');
  const [sort, setSort] = useState<DiscussionSort>('recent');
  const { isAuthenticated } = useAuth();
  const hasDemoItems = items.some((item) => item.author?.is_demo);
  const socialCandidate = supportedSocialLinkIn(body);
  const sortedItems = useMemo(() => [...items].sort((left, right) => {
    if (sort === 'popular') {
      const leftScore = (left.reactions?.like || 0) + (left.reactions?.insightful || 0);
      const rightScore = (right.reactions?.like || 0) + (right.reactions?.insightful || 0);
      return rightScore - leftScore || Date.parse(right.created_at) - Date.parse(left.created_at);
    }
    if (sort === 'discussed') return right.reply_count - left.reply_count || Date.parse(right.created_at) - Date.parse(left.created_at);
    return Date.parse(right.created_at) - Date.parse(left.created_at) || right.id - left.id;
  }), [items, sort]);

  useEffect(() => setSelectedIssue(issue), [issue]);
  useEffect(() => setPostKind(proposalsOnly ? 'proposal' : 'discussion'), [proposalsOnly]);

  useEffect(() => {
    if (issue || !socialCandidate || !isSupportedSocialLink(socialCandidate)) {
      setSuggestionState('idle');
      setSuggestedTitle('');
      if (!issue) setSelectedIssue('');
      return;
    }
    let active = true;
    const timeout = window.setTimeout(() => {
      setSuggestionState('loading');
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
          }
        })
        .catch(() => {
          if (!active) return;
          setSelectedIssue('');
          setSuggestedTitle('');
          setSuggestionState('error');
        });
    }, 500);
    return () => { active = false; window.clearTimeout(timeout); };
  }, [issue, socialCandidate]);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(''); setItems([]);
    fetchPublicDiscussions(issue || undefined, videoId || undefined, 0, PAGE_SIZE, view)
      .then((result) => { if (active) { setItems(result.items); setTotal(result.total); } })
      .catch((reason) => active && setError(reason instanceof Error ? reason.message : `${proposalsOnly ? 'Proposals' : 'Discussions'} could not load.`))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [issue, proposalsOnly, videoId, view]);

  useEffect(() => {
    if (!compose) return;
    if (typeof composer.current?.scrollIntoView === 'function') composer.current.scrollIntoView({ block: 'start' });
    composer.current?.querySelector<HTMLTextAreaElement>('textarea')?.focus();
  }, [compose, isAuthenticated]);

  const loadMore = async () => {
    setLoadingMore(true); setError('');
    try {
      const result = await fetchPublicDiscussions(issue || undefined, videoId || undefined, items.length, PAGE_SIZE, view);
      setItems((current) => [...current, ...result.items]); setTotal(result.total);
    } catch (reason) { setError(reason instanceof Error ? reason.message : `More ${proposalsOnly ? 'proposals' : 'discussions'} could not load.`); }
    finally { setLoadingMore(false); }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setNotice(''); setSubmitting(true);
    try {
      const socialLink = supportedSocialLinkIn(body);
      const note = socialLink ? body.replace(socialLink, '').trim() : body.trim();
      const postBody = note;
      if (postBody.length > 10000) throw new Error('Shorten your post before adding this link.');
      if (postKind === 'proposal' && !selectedIssue) throw new Error('Open an Agenda issue before proposing a solution.');
      const result = postKind === 'proposal'
        ? await createCitizenSolution({ issue_slug: selectedIssue, title: (postBody.split(/\n|[.!?]\s/)[0] || 'Community proposal').slice(0, 100), summary: postBody.slice(0, 1000), body: postBody, ...(socialLink ? { video_url: socialLink } : {}) })
        : await createDiscussion({ body: postBody, ...(socialLink ? { video_url: socialLink } : {}), ...(selectedIssue ? { issue_slug: selectedIssue } : {}) });
      setBody(''); setSelectedIssue(issue); setSuggestedTitle('');
      const published = !('moderation_status' in result) || result.moderation_status === 'published';
      setNotice(published ? (postKind === 'proposal' ? 'Proposal published.' : socialLink ? 'Video shared in Videos.' : 'Discussion posted.') : `${'message' in result ? result.message : 'Submitted'}. It will appear here after review.`);
      if (published) {
        const refreshed = await fetchPublicDiscussions(issue || undefined, videoId || undefined, 0, PAGE_SIZE, view);
        setItems(refreshed.items);
        setTotal(refreshed.total);
      }
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to submit post.'); }
    finally { setSubmitting(false); }
  };

  return <main className="min-h-screen bg-bg px-4 py-8 text-text-1 sm:px-6 sm:py-12">
    <div className="mx-auto max-w-3xl">
      <header className="border-b border-border pb-5">
        <h1 className="font-display text-4xl sm:text-5xl">{proposalsOnly ? 'Proposals' : 'Discussions'}</h1>
        {videoId && <div className="mt-5 rounded-xl border border-accent/30 bg-accent/5 p-4"><p className="text-sm text-text-2">Showing the conversation connected to this video.</p><Link className="mt-2 inline-block font-semibold text-accent-text underline" to="/discuss">Return to the full feed</Link></div>}
        {issue && <div className="mt-5 rounded-xl border border-accent/30 bg-accent/5 p-4"><p className="text-sm text-text-2">Showing conversation connected to this issue's reviewed civic record.</p><Link className="mt-2 inline-block font-semibold text-accent-text underline" to={`/issues/${issue}`}>Return to official issue evidence</Link></div>}
      </header>

      <div className="mt-5">
        <div className="min-w-0">
          <section ref={composer} id="composer" className="scroll-mt-20 rounded-2xl border border-border bg-surface p-3" aria-label="Create a civic post">
            {isAuthenticated ? <form className="space-y-3" onSubmit={submit}>
              <div className="flex flex-wrap items-start gap-3 sm:flex-nowrap"><div aria-hidden="true" className="grid h-11 w-11 shrink-0 place-content-center rounded-full bg-accent/15 font-bold text-accent-text">You</div><label className="sr-only" htmlFor="discussion-composer">Create a post</label><textarea id="discussion-composer" className="min-h-12 min-w-0 flex-1 resize-y rounded-2xl border-0 bg-bg px-5 py-3 text-base leading-6 text-text-1 outline-none focus-visible:ring-4 focus-visible:ring-accent/30" minLength={postKind === 'proposal' ? 20 : undefined} maxLength={10000} rows={postKind === 'proposal' ? 4 : 1} placeholder={postKind === 'proposal' ? 'Describe your proposed solution…' : 'Write something or paste a link…'} value={body} onChange={(event) => setBody(event.target.value)} /><button disabled={submitting || !body.trim() || (postKind === 'proposal' && body.trim().length < 20)} className="ml-auto min-h-12 rounded-full bg-accent px-6 py-3 font-bold text-white disabled:opacity-40">{submitting ? 'Publishing…' : postKind === 'proposal' ? 'Publish proposal' : 'Post'}</button></div>
              {postKind === 'proposal' && <p className="text-sm text-text-2">Published as a structured proposal with one Community conversation and Support/Oppose voting.</p>}
              {!proposalsOnly && socialCandidate && <p className="text-sm text-text-2">Video links are published to Videos, not the Discussions feed.</p>}
              {socialCandidate && isSupportedSocialLink(socialCandidate) && !issue && <div aria-live="polite" className="rounded-xl border border-border bg-bg p-4">
                {suggestionState === 'loading' && <p className="text-sm text-text-2">Matching this video automatically…</p>}
                {suggestionState === 'ready' && <p className="text-sm text-text-2">Filed automatically under <strong className="text-text-1">{suggestedTitle}</strong>.</p>}
                {suggestionState === 'unmatched' && <p className="text-sm text-text-2">We will post the link as shared.</p>}
                {suggestionState === 'error' && <p className="text-sm text-text-2">We will match the topic when you post.</p>}
              </div>}
            </form> : <Link className="flex min-h-12 items-center gap-3" to={`/login?next=${encodeURIComponent(compose ? '/discuss?compose=1#composer' : '/discuss')}`}><span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-content-center rounded-full bg-accent/15 font-bold text-accent-text">You</span><span className="flex-1 rounded-full bg-bg px-5 py-3 text-text-2">Sign in to write something or paste a link…</span></Link>}
            {notice && <p role="status" className="mt-4 text-sm text-accent-text">{notice}</p>}
          </section>

          {loading && <div className="mt-6 space-y-4" aria-label="Loading latest discussions"><div className="h-56 animate-pulse rounded-2xl border border-border bg-surface" /><div className="h-56 animate-pulse rounded-2xl border border-border bg-surface" /></div>}
          {error && <div role="alert" className="mt-6 rounded-2xl border border-red-300 bg-red-50 p-5 text-red-800">{error}<button type="button" onClick={() => window.location.reload()} className="ml-3 font-bold underline">Try again</button></div>}
          {!loading && !error && items.length === 0 && <div className="mt-6 rounded-2xl border border-dashed border-border bg-surface p-8 text-center"><h2 className="text-xl font-semibold">No {proposalsOnly ? 'proposals' : 'discussions'} here yet</h2><p className="mt-2 text-text-2">{videoId ? 'No published conversation is connected to this video yet.' : proposalsOnly ? 'Open an Agenda issue to propose a solution.' : 'Be the first to start a text conversation or share a supporting link.'}</p><Link className="mt-5 inline-block font-semibold text-accent-text underline" to={proposalsOnly ? '/civic' : '/discuss?compose=1#composer'}>{proposalsOnly ? 'Explore the Agenda' : 'Start a discussion'}</Link></div>}

          {!loading && !error && items.length > 0 && <div className="mt-5 flex items-center justify-between gap-3"><p className="shrink-0 text-sm text-text-3">{total} {total === 1 ? (proposalsOnly ? 'proposal' : 'thread') : (proposalsOnly ? 'proposals' : 'threads')}</p><label className="sr-only" htmlFor="discussion-sort">Sort</label><select id="discussion-sort" value={sort} onChange={(event) => setSort(event.target.value as DiscussionSort)} className="min-h-10 rounded-xl border border-border bg-surface px-3 text-sm font-semibold text-text-1 outline-none focus-visible:ring-4 focus-visible:ring-accent/30"><option value="recent">Most recent</option><option value="popular">Most popular</option><option value="discussed">Most discussed</option></select></div>}
          {!loading && !error && hasDemoItems && <aside role="note" className="mt-4 rounded-xl border border-amber-500/40 bg-amber-300/10 p-4 text-sm leading-6 text-text-2"><strong className="text-text-1">Visual demo:</strong> Latin placeholder posts, numbered test users, replies, and reactions are shown here to test the civic feed. They are not real civic participation.</aside>}
          <section aria-label="Latest civic discussions" className="mt-4 space-y-4 sm:space-y-5">{sortedItems.map((item) => <DiscussionPostCard key={item.id} item={item} isAuthenticated={isAuthenticated} mode={proposalsOnly ? 'proposal' : 'discussion'} />)}</section>
          {items.length < total && <div className="mt-6 text-center"><button type="button" disabled={loadingMore} onClick={() => void loadMore()} className="min-h-11 rounded-full border border-border bg-surface px-6 font-bold text-text-1 disabled:opacity-60">{loadingMore ? 'Loading…' : `Load more (${total - items.length} remaining)`}</button></div>}
        </div>
      </div>
    </div>
  </main>;
}
