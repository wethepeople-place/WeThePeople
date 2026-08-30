import { Navigate, useParams } from 'react-router-dom';

/** Preserve old bookmarks while presenting proposals inside the single Community feed. */
export default function SolutionsPage() {
  const { slug = 'housing-rent' } = useParams();
  return <Navigate replace to={`/discuss?issue=${encodeURIComponent(slug)}&view=proposals`} />;
}
