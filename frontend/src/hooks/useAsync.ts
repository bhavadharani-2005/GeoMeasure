import { useCallback, useEffect, useRef, useState } from "react";
import { toApiError } from "../api/client";

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/** Runs ``loader`` on mount and whenever ``deps`` change; ignores stale responses. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<{ data: T | null; error: string | null; loading: boolean }>({
    data: null,
    error: null,
    loading: true,
  });
  const [tick, setTick] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    loaderRef
      .current()
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((err) => !cancelled && setState({ data: null, error: toApiError(err).message, loading: false }));
    return () => {
      cancelled = true;
    };
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
