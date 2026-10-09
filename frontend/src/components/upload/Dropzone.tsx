import { FileUp, X } from "lucide-react";
import { useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { formatBytes } from "../../utils/format";

export const ACCEPTED_EXTENSIONS = [".kml", ".zip"];

interface Props {
  file: File | null;
  maxMb: number;
  disabled?: boolean;
  onSelect: (file: File | null) => void;
}

export function Dropzone({ file, maxMb, disabled, onSelect }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const browse = () => !disabled && inputRef.current?.click();
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      browse();
    }
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (!disabled) onSelect(e.dataTransfer.files[0] ?? null);
  };

  if (file) {
    const ext = file.name.includes(".") ? file.name.split(".").pop()!.toUpperCase() : "—";
    return (
      <div className="selected-file">
        <FileUp size={22} strokeWidth={1.5} aria-hidden="true" />
        <div className="selected-file__info">
          <div className="selected-file__name truncate">{file.name}</div>
          <div className="selected-file__meta">
            {ext} · {formatBytes(file.size)}
          </div>
        </div>
        <button
          type="button"
          className="btn btn--ghost btn--icon"
          onClick={() => onSelect(null)}
          disabled={disabled}
          aria-label="Remove selected file"
        >
          <X size={18} />
        </button>
      </div>
    );
  }

  return (
    <div
      className={`dropzone${dragging ? " dropzone--active" : ""}`}
      role="button"
      tabIndex={0}
      aria-label="Choose a file to upload"
      onClick={browse}
      onKeyDown={onKey}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <FileUp size={30} strokeWidth={1.4} aria-hidden="true" />
      <p className="dropzone__title">Drop a file here, or click to browse</p>
      <p className="dropzone__hint">
        Supported: <strong>.kml</strong> or <strong>.zip</strong> (Shapefile) · Max {maxMb} MB
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        hidden
        onChange={(e) => {
          onSelect(e.target.files?.[0] ?? null);
          e.target.value = "";
        }}
      />
    </div>
  );
}
