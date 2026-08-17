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
    { label: 'ACT', to: returnToVideoId
      ? `/act?target_type=video&target_id=${encodeURIComponent(returnToVideoId)}`
      : `/act?target_type=issue&target_id=${encodeURIComponent(issueSlug)}` },
    { label: 'Elections', to: `/elections?issue=${encodeURIComponent(issueSlug)}` },
  ];

  return <nav aria-label="Issue actions" className="grid min-w-0 grid-cols-2 gap-2 sm:grid-cols-4 [&_a]:flex [&_a]:min-h-11 [&_a]:min-w-0 [&_a]:items-center [&_a]:justify-center [&_a]:rounded-full [&_a]:border [&_a]:border-amber-300/45 [&_a]:bg-amber-300/10 [&_a]:px-3 [&_a]:py-2.5 [&_a]:text-center [&_a]:text-sm [&_a]:font-bold [&_a]:leading-tight [&_a]:text-amber-300 [&_a]:outline-none [&_a]:transition [&_a]:hover:bg-amber-300/20 [&_a]:focus-visible:ring-4 [&_a]:focus-visible:ring-amber-300/70">
    {actions.map((action) => <Link key={action.label} to={action.to} state={state}>{action.label}</Link>)}
  </nav>;
}
