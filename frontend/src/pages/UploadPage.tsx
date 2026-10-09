import { Loader2 } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toApiError } from "../api/client";
import { filesApi } from "../api/files";
import { PageHeader } from "../components/layout/PageHeader";
import { Dropzone, ACCEPTED_EXTENSIONS } from "../components/upload/Dropzone";
import { ErrorNotice } from "../components/ui/Feedback";

const MAX_UPLOAD_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB ?? 25);

export function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const select = (next: File | null) => {
    setError(null);
    if (next) {
      const lower = next.name.toLowerCase();
      if (!ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
        setError("Only .kml files and zipped Shapefiles (.zip) are supported.");
        return;
      }
      if (next.size > MAX_UPLOAD_MB * 1024 * 1024) {
        setError(`The file exceeds the ${MAX_UPLOAD_MB} MB upload limit.`);
        return;
      }
    }
    setFile(next);
  };

  const submit = async () => {
    if (!file || inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await filesApi.upload(file);
      navigate(`/files/${result.id}`);
    } catch (err) {
      setError(toApiError(err).message);
      setBusy(false);
    } finally {
      inFlight.current = false;
    }
  };

  return (
    <>
      <PageHeader title="Upload" subtitle="Add a spatial dataset to measure." />
      <section className="panel upload-panel">
        <h2 className="panel__title">Upload spatial data</h2>
        <p className="muted">Upload a KML file or a zipped ESRI Shapefile.</p>
        <Dropzone file={file} maxMb={MAX_UPLOAD_MB} disabled={busy} onSelect={select} />
        {error && <ErrorNotice message={error} />}
        <div className="upload-panel__footer">
          <p className="muted" aria-live="polite">
            {busy ? "Processing spatial features…" : "Shapefiles must include .shp, .shx, .dbf and .prj."}
          </p>
          <button type="button" className="btn btn--primary" disabled={!file || busy} onClick={submit}>
            {busy && <Loader2 size={16} className="spin" aria-hidden="true" />}
            {busy ? "Processing" : "Process file"}
          </button>
        </div>
      </section>
    </>
  );
}
