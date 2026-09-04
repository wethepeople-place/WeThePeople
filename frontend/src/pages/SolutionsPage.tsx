import { Navigate, useParams } from 'react-router-dom';

/** Preserve old bookmarks while presenting proposals in their dedicated view. */
export default function SolutionsPage() {
  const { slug = 'housing-rent' } = useParams();
  return <Navigate replace to={`/proposals?issue=${encodeURIComponent(slug)}`} />;
}
