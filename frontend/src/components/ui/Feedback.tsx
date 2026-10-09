import { AlertTriangle, RotateCw } from "lucide-react";

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="notice notice--error" role="alert">
      <AlertTriangle size={18} aria-hidden="true" />
      <span className="notice__text">{message}</span>
      {onRetry && (
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>
          <RotateCw size={14} aria-hidden="true" /> Retry
        </button>
      )}
    </div>
  );
}

export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: string }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function PanelSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="stack" role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height={18} width={i === 0 ? "40%" : "100%"} />
      ))}
    </div>
  );
}
