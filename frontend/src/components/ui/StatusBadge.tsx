import type { FileStatus } from "../../types/api";

const LABELS: Record<FileStatus, string> = {
  COMPLETED: "Completed",
  PROCESSING: "Processing",
  FAILED: "Failed",
};

export function StatusBadge({ status }: { status: FileStatus }) {
  return (
    <span className={`badge badge--${status.toLowerCase()}`}>
      <span className="badge__dot" aria-hidden="true" />
      {LABELS[status]}
    </span>
  );
}
