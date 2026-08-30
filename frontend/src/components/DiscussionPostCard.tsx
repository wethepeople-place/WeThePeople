import { useMemo, useState } from 'react';
import { Bookmark, ExternalLink, Flag, Heart, Lightbulb, MessageCircle, Play, Share2, ThumbsDown } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

import {
  reportDiscussionPost,
  setDiscussionBookmark,
  setDiscussionReaction,
  type DiscussionReaction,
  type PublicDiscussionPost,
} from '../api/civic';
import DiscussionVideoEmbed from './DiscussionVideoEmbed';

type Props = {
  item: PublicDiscussionPost;
  isAuthenticated: boolean;
};

const reactionMeta: Array<{ value: DiscussionReaction; label: string; Icon: typeof Heart }> = [
  { value: 'like', label: 'Like', Icon: Heart },
  { value: 'insightful', label: 'Insightful', Icon: Lightbulb },
  { value: 'disagree', label: 'Disagree', Icon: ThumbsDown },
];

function attachmentUrl(attachment: PublicDiscussionPost['attachments'][number], attachments: PublicDiscussionPost['attachments']): string | null {
  switch (attachment.type) {
    case 'video': return `/discuss?video=${encodeURIComponent(attachment.reference_id)}`;
    case 'issue': return `/issues/${attachment.reference_id}`;
    case 'bill': return `/politics/bill/${attachment.reference_id}`;
    case 'politician': return `/politics/people/${attachment.reference_id}`;
    case 'solution': {
      const issue = attachments.find((value) => value.type === 'issue');
      return issue ? `/issues/${issue.reference_id}/solutions/${attachment.reference_id}` : null;
    }
    default: return null;
  }
}

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'W';
}

function linkedText(body: string, postId: number) {
  const urlPattern = /(https:\/\/[^\s]+)/g;
  return body.split(urlPattern).map((part, index) => part.match(/^https:\/\//)
    ? <a key={`${part}-${index}`} href={part} target="_blank" rel="noreferrer" className="break-all font-semibold text-accent-text underline">{part}<span className="sr-only"> (opens in a new tab)</span></a>
    : part ? <Link key={`text-${index}`} to={`/discuss/${postId}`} className="hover:text-accent-text">{part}</Link> : null);
}

export default function DiscussionPostCard({ item, isAuthenticated }: Props) {
  const proposal = item.attachments.find((attachment) => attachment.type === 'solution');
  const location = useLocation();
  const [reactions, setReactions] = useState(item.reactions || { like: 0, insightful: 0, disagree: 0 });
  const [viewerReactions, setViewerReactions] = useState<DiscussionReaction[]>(item.viewer_reactions || []);
  const [bookmarked, setBookmarked] = useState(Boolean(item.viewer_bookmarked));
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [reporting, setReporting] = useState(false);
  const [reportReason, setReportReason] = useState('misinformation');
  const [reportDetails, setReportDetails] = useState('');
  const loginUrl = `/login?next=${encodeURIComponent(`${location.pathname}${location.search}`)}`;
  const created = useMemo(() => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.created_at)), [item.created_at]);
  const reviewedVideo = item.attachments.find((attachment) => attachment.type === 'video');

  const toggleReaction = async (reaction: DiscussionReaction) => {
    const enabled = !viewerReactions.includes(reaction);
    setBusy(reaction); setError(''); setNotice('');
    try {
      const result = await setDiscussionReaction(item.id, reaction, enabled);
      setReactions(result.reactions);
      setViewerReactions((current) => enabled ? [...current, reaction] : current.filter((value) => value !== reaction));
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Reaction could not be saved.'); }
    finally { setBusy(''); }
  };

  const toggleBookmark = async () => {
    setBusy('bookmark'); setError(''); setNotice('');
    try { const result = await setDiscussionBookmark(item.id, !bookmarked); setBookmarked(result.bookmarked); setNotice(result.bookmarked ? 'Saved privately.' : 'Removed from private saves.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Save could not be updated.'); }
    finally { setBusy(''); }
  };

  const share = async () => {
    const url = new URL(`/discuss/${item.id}`, window.location.origin).toString();
    try {
      if (navigator.share) await navigator.share({ title: 'WeThePeople civic discussion', text: item.body.slice(0, 180), url });
      else { await navigator.clipboard.writeText(url); setNotice('Discussion link copied.'); }
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === 'AbortError') return;
      setError('The discussion link could not be shared.');
    }
  };

  const submitReport = async () => {
    setBusy('report'); setError('');
    try { await reportDiscussionPost(item.id, reportReason, reportDetails.trim() || undefined); setReporting(false); setReportDetails(''); setNotice('Report received privately for review.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Report could not be submitted.'); }
    finally { setBusy(''); }
  };

  return <article className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm" aria-labelledby={`discussion-${item.id}`}>
    <div className="p-5 sm:p-6">
      <header className="flex items-start gap-3">
        <div aria-hidden="true" className="grid h-11 w-11 shrink-0 place-content-center rounded-full bg-accent/15 text-sm font-bold text-accent-text">{initials(item.author.display_name)}</div>
        <div className="min-w-0 flex-1"><p className="truncate font-semibold text-text-1">{item.author.display_name}</p><time className="text-xs text-text-3" dateTime={item.created_at}>{created}</time></div>
        {item.author.is_demo && <span className="rounded-full border border-amber-500/50 bg-amber-300/10 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-amber-700 dark:text-amber-300">Demo data</span>}
        <span className="rounded-full border border-border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-text-3">Published</span>
      </header>
      {proposal && <p className="mt-4 inline-flex rounded-full bg-accent/15 px-3 py-1 text-xs font-black uppercase tracking-wider text-accent-text">Community proposal</p>}

      <div id={`discussion-${item.id}`} className="mt-4 whitespace-pre-wrap text-lg leading-8 text-text-1">{linkedText(item.body, item.id)}</div>
      {item.video_link && <DiscussionVideoEmbed video={item.video_link} title={`Video shared by ${item.author.display_name}`} postId={item.id} />}
      {reviewedVideo && <Link aria-label={`Open video conversation, ${item.reply_count} ${item.reply_count === 1 ? 'reply' : 'replies'}`} className="mt-4 flex min-h-12 w-full items-center justify-between gap-3 rounded-xl bg-accent px-4 py-2.5 text-sm font-bold text-white shadow-sm sm:inline-flex sm:w-auto sm:rounded-full" to={`/discuss?video=${encodeURIComponent(reviewedVideo.reference_id)}`}><span className="inline-flex items-center gap-2"><Play className="h-4 w-4 fill-current" />Open video conversation</span><span className="whitespace-nowrap text-xs font-semibold text-white/80">{item.reply_count} {item.reply_count === 1 ? 'reply' : 'replies'}</span></Link>}

      {item.attachments.length > 0 && <aside aria-label="Civic context" className="mt-4 flex flex-wrap gap-2">{item.attachments.map((attachment) => {
        const url = attachmentUrl(attachment, item.attachments);
        const label = attachment.label || attachment.source?.publisher || `${attachment.type}: ${attachment.reference_id}`;
        if (attachment.type === 'source' && attachment.source) return <a key={`${attachment.type}-${attachment.reference_id}`} className="inline-flex min-h-9 items-center gap-1 rounded-full border border-accent/40 px-3 py-1 text-sm font-semibold text-accent-text" href={attachment.source.url} target="_blank" rel="noreferrer">{label}<ExternalLink className="h-3.5 w-3.5" /></a>;
        return url ? <Link key={`${attachment.type}-${attachment.reference_id}`} className="inline-flex min-h-9 items-center rounded-full border border-accent/40 px-3 py-1 text-sm font-semibold text-accent-text" to={url}>{label}</Link> : <span key={`${attachment.type}-${attachment.reference_id}`} className="inline-flex min-h-9 items-center rounded-full border border-border px-3 py-1 text-sm text-text-2">{label}</span>;
      })}</aside>}

      <div className="mt-5 flex flex-wrap items-center gap-1 border-t border-border pt-3" aria-label="Discussion actions">
        <Link className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm text-text-2 hover:bg-bg hover:text-accent-text" to={`/discuss/${item.id}`} aria-label={`${item.reply_count} ${item.reply_count === 1 ? 'reply' : 'replies'}`}><MessageCircle className="h-4 w-4" />{item.reply_count}</Link>
        {reactionMeta.map(({ value, label, Icon }) => isAuthenticated ? <button key={value} type="button" disabled={Boolean(busy)} aria-pressed={viewerReactions.includes(value)} onClick={() => void toggleReaction(value)} className={`inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm hover:bg-bg ${viewerReactions.includes(value) ? 'font-bold text-accent-text' : 'text-text-2'}`} aria-label={`${label}: ${reactions[value] || 0}`}><Icon className={`h-4 w-4 ${value === 'like' && viewerReactions.includes(value) ? 'fill-current' : ''}`} />{reactions[value] || 0}</button> : <Link key={value} to={loginUrl} className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm text-text-2" aria-label={`Sign in to ${label.toLowerCase()}`}><Icon className="h-4 w-4" />{reactions[value] || 0}</Link>)}
        {isAuthenticated ? <button type="button" disabled={Boolean(busy)} aria-pressed={bookmarked} onClick={() => void toggleBookmark()} className={`ml-auto inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm hover:bg-bg ${bookmarked ? 'font-bold text-accent-text' : 'text-text-2'}`} aria-label={bookmarked ? 'Remove private save' : 'Save privately'}><Bookmark className={`h-4 w-4 ${bookmarked ? 'fill-current' : ''}`} />Save</button> : <Link to={loginUrl} className="ml-auto inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm text-text-2" aria-label="Sign in to save privately"><Bookmark className="h-4 w-4" />Save</Link>}
        <button type="button" onClick={() => void share()} className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm text-text-2 hover:bg-bg" aria-label="Share discussion"><Share2 className="h-4 w-4" />Share</button>
        {isAuthenticated ? <button type="button" onClick={() => setReporting((value) => !value)} className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm text-text-2 hover:bg-bg" aria-expanded={reporting} aria-controls={`report-${item.id}`}><Flag className="h-4 w-4" />Report</button> : <Link to={loginUrl} className="inline-flex min-h-11 items-center gap-1.5 rounded-full px-3 text-sm text-text-2"><Flag className="h-4 w-4" />Report</Link>}
      </div>

      {reporting && <div id={`report-${item.id}`} className="mt-3 rounded-xl border border-border bg-bg p-4"><label className="text-sm font-semibold">Why are you reporting this?<select value={reportReason} onChange={(event) => setReportReason(event.target.value)} className="mt-2 block w-full rounded-lg border border-border bg-surface px-3 py-2"><option value="misinformation">Potential misinformation</option><option value="harassment">Harassment</option><option value="privacy">Private information</option><option value="spam">Spam</option><option value="other">Other</option></select></label><label className="mt-3 block text-sm font-semibold">Optional context<textarea maxLength={2000} value={reportDetails} onChange={(event) => setReportDetails(event.target.value)} className="mt-2 min-h-20 w-full rounded-lg border border-border bg-surface px-3 py-2" /></label><div className="mt-3 flex gap-2"><button type="button" disabled={busy === 'report'} onClick={() => void submitReport()} className="min-h-11 rounded-full bg-accent px-4 font-bold text-white">Send private report</button><button type="button" onClick={() => setReporting(false)} className="min-h-11 rounded-full border border-border px-4">Cancel</button></div></div>}
      {error && <p role="alert" className="mt-3 text-sm text-red-600">{error}</p>}
      {notice && <p role="status" className="mt-3 text-sm text-accent-text">{notice}</p>}
    </div>
  </article>;
}
