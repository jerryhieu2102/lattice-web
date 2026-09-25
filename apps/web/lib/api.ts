export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { "x-lattice-request": "1" };
  if (body && !(body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const r = await fetch("/api/v1" + path, {
    method,
    credentials: "same-origin",
    headers,
    body:
      body instanceof FormData
        ? body
        : body === undefined
          ? undefined
          : JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Invalid input. Check all required fields, amounts, dates, and currency precision.",
    );
  return data as T;
}
