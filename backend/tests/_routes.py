"""🗺 2026-11-17: every route of an app, in the order the app matches them. Production runs FastAPI 0.141 (backend/.venv), where an included router
stays ONE `_IncludedRouter` entry in app.routes (no .path); older FastAPI copies its routes in. A test that walks app.routes directly saw no
included route at all on 0.141, so a route guard there passed on nothing. Walk routes with this instead."""


def flat_routes(app):
    out = []

    def walk(routes):
        for r in routes:
            inner = getattr(r, 'original_router', None)
            if inner is not None:
                walk(inner.routes)
            else:
                out.append(r)
    walk(app.routes)
    return out
