import { FolderOpen, Upload } from "lucide-react";
import { Link } from "react-router-dom";
import { filesApi } from "../api/files";
import { FilesTable } from "../components/files/FilesTable";
import { PageHeader } from "../components/layout/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorNotice, PanelSkeleton } from "../components/ui/Feedback";
import { useAsync } from "../hooks/useAsync";
import { formatInt } from "../utils/format";

const RECENT_COUNT = 8;
const LINE_TYPES = ["LineString", "MultiLineString"];
const POLYGON_TYPES = ["Polygon", "MultiPolygon"];

const sumOf = (counts: Record<string, number>, keys: string[]) =>
  keys.reduce((total, key) => total + (counts[key] ?? 0), 0);

export function OverviewPage() {
  const stats = useAsync(() => filesApi.stats(), []);
  const files = useAsync(() => filesApi.list(RECENT_COUNT), []);

  const cards = stats.data && [
    { label: "Files processed", value: stats.data.files_completed },
    { label: "Total features", value: stats.data.features_total },
    { label: "Polygons", value: sumOf(stats.data.geometry_counts, POLYGON_TYPES) },
    { label: "Line features", value: sumOf(stats.data.geometry_counts, LINE_TYPES) },
  ];

  return (
    <>
      <PageHeader
        title="Overview"
        subtitle="Upload and inspect spatial datasets and calculated measurements."
        actions={
          <Link to="/upload" className="btn btn--primary">
            <Upload size={16} aria-hidden="true" /> Upload
          </Link>
        }
      />

      {stats.error ? (
        files.error ? null : (
        <ErrorNotice message={stats.error} onRetry={stats.reload} />
        )
      ) : (
        <section className="stat-grid" aria-label="Summary">
          {(cards ?? Array.from({ length: 4 }, () => null)).map((card, i) => (
            <div className="stat" key={card?.label ?? i}>
              <div className="stat__label">{card?.label ?? " "}</div>
              <div className="stat__value">{card ? formatInt(card.value) : "–"}</div>
            </div>
          ))}
        </section>
      )}

      <section className="panel">
        <div className="panel__head">
          <h2 className="panel__title">Recent files</h2>
          <Link to="/files" className="link">
            View all
          </Link>
        </div>
        {files.loading ? (
          <PanelSkeleton />
        ) : files.error ? (
          <ErrorNotice message={files.error} onRetry={files.reload} />
        ) : files.data && files.data.length > 0 ? (
          <FilesTable files={files.data} />
        ) : (
          <EmptyState
            icon={FolderOpen}
            title="No files uploaded yet"
            action={
              <Link to="/upload" className="btn btn--primary btn--sm">
                Upload your first file
              </Link>
            }
          >
            Upload a KML file or zipped Shapefile to see its features and measurements here.
          </EmptyState>
        )}
      </section>
    </>
  );
}
