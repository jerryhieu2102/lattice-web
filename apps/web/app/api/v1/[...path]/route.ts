import { NextRequest } from "next/server";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const target =
    (process.env.API_INTERNAL_URL || "http://127.0.0.1:8000") +
    "/api/v1/" +
    path.map(encodeURIComponent).join("/") +
    request.nextUrl.search;
  const headers = new Headers();
  for (const key of ["content-type", "cookie", "x-lattice-request"]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }
  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await request.arrayBuffer(),
      cache: "no-store",
      signal: AbortSignal.timeout(120000),
    });
    const outgoing = new Headers();
    for (const key of ["content-type", "set-cookie", "content-disposition"]) {
      const value = upstream.headers.get(key);
      if (value) outgoing.set(key, value);
    }
    outgoing.set("Cache-Control", "no-store");
    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: outgoing,
    });
  } catch {
    return Response.json(
      { detail: "The API is unavailable. Start the backend and database." },
      { status: 503 },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as PATCH, proxy as DELETE };
