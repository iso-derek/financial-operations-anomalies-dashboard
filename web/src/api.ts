import { useCallback, useEffect, useState } from "react";

export function apiUrl(path: string, params: Record<string, string | number | undefined> = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const text = query.toString();
  return `/api/${path}${text ? `?${text}` : ""}`;
}

export async function send<T>(url: string, method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let message = `Something went wrong (${response.status}).`;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") message = data.detail;
      else if (Array.isArray(data?.detail)) message = "Please check the values you entered.";
    } catch {
      /* keep default */
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export interface Loadable<T> { data: T | undefined; error: string | undefined; loading: boolean; reload: () => void }

/** Fetch JSON; keeps showing the last result while refreshing. Call reload() after a change. */
export function useApi<T>(url: string | null): Loadable<T> {
  const [state, setState] = useState<Omit<Loadable<T>, "reload">>({ data: undefined, error: undefined, loading: url !== null });
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((value) => value + 1), []);
  useEffect(() => {
    if (url === null) return;
    let live = true;
    setState((previous) => ({ ...previous, loading: true, error: undefined }));
    send<T>(url)
      .then((data) => live && setState({ data, error: undefined, loading: false }))
      .catch((error: Error) => live && setState((previous) => ({ ...previous, error: error.message, loading: false })));
    return () => {
      live = false;
    };
  }, [url, tick]);
  return { ...state, reload };
}
