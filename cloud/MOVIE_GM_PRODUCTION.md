# Movie GM production path

Movie GM now has a production compute path that preserves the existing Python
decision engine instead of rewriting it in JavaScript.

## Architecture

Browser -> universal-watcher-api JS Worker -> MOVIE_GM Service Binding ->
universal-watcher-movie-gm Python Worker -> TMDB/JustWatch + OMDb

Both Workers bind to the same D1 database. The JS Worker owns private-beta
authentication, CSRF, household profile writes, and feedback writes. The
Python Worker reads the authenticated user's feedback and household profiles,
runs the deterministic Movie GM pipeline, and returns the recommendation
payload.

Cloudflare Service Bindings are internal Worker-to-Worker calls, so the Movie
GM Python Worker does not need a public route. The two Workers are deployed
separately, with the Python Worker deployed first.

## Deployment prerequisites

1. Apply migrations 0001 through 0006 to the production D1 database.
2. Put the real D1 database ID in both Worker Wrangler configurations.
3. Deploy universal-watcher-movie-gm using movie-gm-wrangler.example.toml.
4. Configure the Python Worker secrets: TMDB_READ_ACCESS_TOKEN and OMDB_API_KEY.
5. Deploy universal-watcher-api using cloud/wrangler.example.toml.
6. Configure the existing JS Worker secrets: ACCESS_SECRET and SESSION_KEY,
   plus the existing worker secret configuration required by the current API.
7. Open the Worker origin. The browser will show the private-beta access dialog
   and establish the signed session before using production Movie GM.

The repository intentionally contains placeholders rather than database IDs or
API credentials.

## Zero-cost design

The production Movie GM path uses Cloudflare Workers, D1, static assets, and a
Service Binding. Service Bindings do not add a separate infrastructure charge.
The repository does not add a paid SaaS dependency.

## Important limitation

The repository can build and test this path, but deployment still requires the
actual Cloudflare account configuration and secrets. Those are not available
through the GitHub repository and are not committed to source control.
