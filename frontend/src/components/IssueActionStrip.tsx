import { Link } from 'react-router-dom';

type Props = {
  issueSlug: string;
  evidenceCount?: number;
  billCount?: number;
  returnToVideoId?: string;
};

export default function IssueActionStrip({ issueSlug, evidenceCount, billCount, returnToVideoId }: Props) {
  const state = returnToVideoId ? { returnToVideoId } : undefined;
  const actions = [
    { label: evidenceCount === undefined ? 'Evidence' : `${evidenceCount} evidence series`, to: `/issues/${issueSlug}#evidence` },
    { label: billCount === undefined ? 'Bills' : `${billCount} reviewed bills`, to: `/issues/${issueSlug}#legislation` },
    { label: 'Solutions', to: `/issues/${issueSlug}/solutions` },
    { label: 'Discuss', to: `/discuss?issue=${encodeURIComponent(issueSlug)}` },
    { label: 'Government', to: `/government?issue=${encodeURIComponent(issueSlug)}` },
    { label: 'Representatives', to: `/politics/find-rep?issue=${encodeURIComponent(issueSlug)}` },
    { label: 'Courts', to: `/courts?issue=${encodeURIComponent(issueSlug)}` },
  ];

  return <nav aria-label="Issue actions" className="flex snap-x gap-3 overflow-x-auto pb-2 [scrollbar-width:thin] [&_a]:shrink-0 [&_a]:snap-start [&_a]:rounded-full [&_a]:border [&_a]:border-amber-300/45 [&_a]:bg-amber-300/10 [&_a]:px-4 [&_a]:py-3 [&_a]:font-bold [&_a]:text-amber-300 [&_a]:outline-none [&_a]:transition [&_a]:hover:bg-amber-300/20 [&_a]:focus-visible:ring-4 [&_a]:focus-visible:ring-amber-300/70">
    {actions.map((action) => <Link key={action.label} to={action.to} state={state}>{action.label}</Link>)}
  </nav>;
}
