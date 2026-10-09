import { Trash2 } from "lucide-react";
import { useState } from "react";

interface Props {
  onConfirm: () => Promise<void> | void;
  label?: string;
  iconOnly?: boolean;
}

/** Two-step delete: first click asks, second click performs the deletion. */
export function DeleteButton({ onConfirm, label = "Delete", iconOnly }: Props) {
  const [armed, setArmed] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!armed) {
    return (
      <button
        type="button"
        className={`btn btn--ghost btn--sm btn--danger-text${iconOnly ? " btn--icon" : ""}`}
        onClick={() => setArmed(true)}
        aria-label={label}
        title={label}
      >
        <Trash2 size={15} aria-hidden="true" />
        {!iconOnly && label}
      </button>
    );
  }
  return (
    <span className="inline-actions">
      <button
        type="button"
        className="btn btn--danger btn--sm"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await onConfirm();
          } finally {
            setBusy(false);
            setArmed(false);
          }
        }}
      >
        {busy ? "Deleting…" : "Confirm"}
      </button>
      <button type="button" className="btn btn--ghost btn--sm" disabled={busy} onClick={() => setArmed(false)}>
        Cancel
      </button>
    </span>
  );
}
