import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { fetchPublicDiscussions, type PublicDiscussionPost } from '../api/civic';

function attachmentUrl(attachment: PublicDiscussionPost['attachments'][number]): string | null {
  switch (attachment.type) {
    case 'video': return `/watch/${attachment.reference_id}`;
    case 'issue': return `/issues/${attachment.reference_id}`;
    case 'bill': return `/politics/bill/${attachment.reference_id}`;
    case 'politician': return `/politics/people/${attachment.reference_id}`;
    case 'solution': return `/issues/housing-rent/solutions/${attachment.reference_id}`;
    default: return null;
  }
}

export default function DiscussionsPage() {
  const [params] = useSearchParams();
  const issue = params.get('issue') || '';
  const [items, setItems] = useState<PublicDiscussionPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetchPublicDiscussions(issue || undefined)
      .then((result) => active && setItems(result.items))
      .catch((reason) => active && setError(reason.message))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [issue]);

  return (
    <main className="min-h-screen bg-bg px-5 py-12 text-text-1">
      <div className="mx-auto max-w-3xl">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent-text">Discuss</p>
        <h1 className="mt-3 font-display text-4xl sm:text-5xl">Public civic discussion</h1>
        <p className="mt-3 max-w-2xl text-text-2">{issue ? 'Conversation connected to this issue’s reviewed evidence, government activity, and citizen solutions.' : 'Conversation connected to reviewed evidence, government activity, and citizen solutions.'}</p>
        {issue && <p className="mt-4"><Link className="text-accent-text underline" to={`/issues/${issue}`}>Return to official issue evidence</Link></p>}

        {loading && <p className="mt-10 text-text-2">Loading discussions…</p>}
        {error && <div className="mt-10 rounded-card border border-border bg-surface p-6 text-text-2">{error}</div>}
        {!loading && !error && items.length === 0 && (
          <div className="mt-10 rounded-card border border-border bg-surface p-8">
            <h2 className="text-xl font-semibold">No published discussions yet</h2>
            <p className="mt-2 text-text-2">Reviewed, source-linked conversations will appear here.</p>
            <Link className="mt-5 inline-block text-accent-text underline" to="/watch">Explore Watch</Link>
          </div>
        )}

        <section className="mt-10 space-y-5">
          {items.map((item) => (
            <article key={item.id} className="rounded-card border border-border bg-surface p-6">
              <Link className="block text-lg leading-8 hover:text-accent-text" to={`/discuss/${item.id}`}>{item.body}</Link>
              <p className="mt-3 text-sm text-text-3">{item.author.display_name} · {item.reply_count} {item.reply_count === 1 ? 'reply' : 'replies'}</p>
              {item.attachments.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {item.attachments.map((attachment) => {
                    const url = attachmentUrl(attachment);
                    const label = attachment.label || `${attachment.type}: ${attachment.reference_id}`;
                    return url ? <Link key={`${attachment.type}-${attachment.reference_id}`} className="rounded-pill border border-accent/40 px-3 py-1 text-sm text-accent-text" to={url}>{label}</Link> : <span key={`${attachment.type}-${attachment.reference_id}`} className="rounded-pill border border-border px-3 py-1 text-sm text-text-2">{label}</span>;
                  })}
                </div>
              )}
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
