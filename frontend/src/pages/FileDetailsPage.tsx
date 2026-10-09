import { ArrowLeft, FileWarning, MapPinOff } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toApiError } from "../api/client";
import { filesApi } from "../api/files";
import { FeatureDetails } from "../components/files/FeatureDetails";
import { FeatureTable } from "../components/files/FeatureTable";
import { PageHeader } from "../components/layout/PageHeader";
import { FeatureMap } from "../components/map/FeatureMap";
import { MapBoundary } from "../components/map/MapBoundary";
import { DeleteButton } from "../components/ui/DeleteButton";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorNotice, PanelSkeleton } from "../components/ui/Feedback";
import { StatusBadge } from "../components/ui/StatusBadge";
import { useAsync } from "../hooks/useAsync";
import type { GeospatialFileDetail } from "../types/api";
import { FILE_TYPE_LABEL, formatBytes, formatDate, formatInt, formatNumber } from "../utils/format";

function MetaGrid({ file }: { file: GeospatialFileDetail }) {
  const items: [string, React.ReactNode][] = [
    ["File type", `${FILE_TYPE_LABEL[file.file_type]} · ${formatBytes(file.file_size)}`],
    ["Features", formatInt(file.feature_count)],
    ["Original CRS", file.original_crs ?? "—"],
    ["Measurement CRS", file.projected_crs ?? "—"],
    ["Status", <StatusBadge status={file.status} />],
    ["Uploaded", formatDate(file.created_at)],
  ];
  return (
    <section className="meta-grid" aria-label="File metadata">
      {items.map(([label, value]) => (
        <div className="meta" key={label}>
          <div className="meta__label">{label}</div>
          <div className="meta__value">{value}</div>
        </div>
      ))}
    </section>
  );
}

function ProcessedView({ file }: { file: GeospatialFileDetail }) {
  const measurements = useAsync(() => filesApi.measurements(file.id), [file.id]);
  const geojson = useAsync(() => filesApi.geojson(file.id), [file.id]);
  const [selected, setSelected] = useState<number | null>(null);

  const features = measurements.data?.features ?? [];
  const selectedFeature = useMemo(
    () => features.find((f) => f.feature_index === selected) ?? null,
    [features, selected],
  );
  const totals = useMemo(() => {
    let area = 0;
    let length = 0;
    for (const f of features) {
      if (f.measurement?.type === "area") area += f.measurement.value;
      if (f.measurement?.type === "length") length += f.measurement.value;
    }
    return { area, length };
  }, [features]);
  const hasMappable = (geojson.data?.features.length ?? 0) > 0;

  return (
    <>
      <div className="split">
        <section className="panel panel--map" aria-label="Map">
          {geojson.loading ? (
            <PanelSkeleton rows={6} />
          ) : geojson.error ? (
            <ErrorNotice message={geojson.error} onRetry={geojson.reload} />
          ) : hasMappable && geojson.data ? (
            <MapBoundary>
              <FeatureMap data={geojson.data} selectedIndex={selected} onSelect={setSelected} />
            </MapBoundary>
          ) : (
            <EmptyState icon={MapPinOff} title="Nothing to display">
              None of the features have geometry that can be drawn on the map.
            </EmptyState>
          )}
        </section>

        <aside className="side">
          <section className="panel">
            <h2 className="panel__title">Dataset summary</h2>
            <dl className="kv">
              {Object.entries(file.geometry_summary).map(([type, count]) => (
                <div className="kv__row" key={type}>
                  <dt>{type}</dt>
                  <dd>{formatInt(count)}</dd>
                </div>
              ))}
              {totals.area > 0 && (
                <div className="kv__row">
                  <dt>Total area</dt>
                  <dd>{formatNumber(totals.area)} m²</dd>
                </div>
              )}
              {totals.length > 0 && (
                <div className="kv__row">
                  <dt>Total length</dt>
                  <dd>{formatNumber(totals.length)} m</dd>
                </div>
              )}
            </dl>
          </section>
          <section className="panel">
            <h2 className="panel__title">Feature details</h2>
            <FeatureDetails feature={selectedFeature} />
          </section>
        </aside>
      </div>

      <section className="panel">
        <h2 className="panel__title">Feature measurements</h2>
        {measurements.loading ? (
          <PanelSkeleton rows={5} />
        ) : measurements.error ? (
          <ErrorNotice message={measurements.error} onRetry={measurements.reload} />
        ) : (
          <FeatureTable features={features} selectedIndex={selected} onSelect={setSelected} />
        )}
      </section>
    </>
  );
}

export function FileDetailsPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const file = useAsync(() => filesApi.get(id), [id]);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const back = (
    <Link to="/files" className="back-link">
      <ArrowLeft size={14} aria-hidden="true" /> All files
    </Link>
  );

  if (file.loading) {
    return (
      <>
        <PageHeader title="Loading…" back={back} />
        <section className="panel">
          <PanelSkeleton rows={4} />
        </section>
      </>
    );
  }
  if (file.error || !file.data) {
    return (
      <>
        <PageHeader title="File" back={back} />
        <ErrorNotice message={file.error ?? "File not found."} onRetry={file.reload} />
      </>
    );
  }

  const data = file.data;
  return (
    <>
      <PageHeader
        title={data.filename}
        back={back}
        actions={
          <DeleteButton
            label="Delete file"
            onConfirm={async () => {
              try {
                await filesApi.remove(data.id);
                navigate("/files");
              } catch (err) {
                setDeleteError(toApiError(err).message);
              }
            }}
          />
        }
      />
      {deleteError && <ErrorNotice message={deleteError} />}
      <MetaGrid file={data} />
      {data.status === "COMPLETED" ? (
        <ProcessedView file={data} />
      ) : (
        <section className="panel">
          <EmptyState icon={FileWarning} title={data.status === "FAILED" ? "Processing failed" : "Processing"}>
            {data.error_message ?? "This file has no processed measurements yet."}
          </EmptyState>
        </section>
      )}
    </>
  );
}
