import Link from 'next/link'
 
export default function NotFound() {
  return (
    <div className="not-found-page">
      <h2 className="not-found-page__title">Not Found</h2>
      <p className="not-found-page__desc">Could not find requested resource</p>
      <Link className="not-found-page__link" href="/">Return Home</Link>
    </div>
  )
}