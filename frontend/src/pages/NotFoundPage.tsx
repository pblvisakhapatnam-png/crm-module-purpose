/**
 * Minimal not-found page for URLs outside the route table.
 *
 * The Next App Router supplied a built-in 404 page. A Vite single-page application serves
 * `index.html` for every path, so an unmatched URL would otherwise render an empty shell.
 *
 * The `<section>` wrapper matches the existing page convention that `app/globals.css` styles
 * through `.app-main > section`.
 *
 * It lives under `src/components/` rather than `src/pages/` on purpose: while Next is still the
 * default runtime, Next treats `src/pages/` as its Pages Router directory and would publish this
 * file as a real `/NotFoundPage` URL. Part 2 may move it once Next is removed.
 */
export default function NotFoundPage() {
  return (
    <section>
      <h2>Page not found</h2>
      <p>The requested page does not exist.</p>
      <p>
        <a href="/">Back to Dashboard</a>
      </p>
    </section>
  );
}
