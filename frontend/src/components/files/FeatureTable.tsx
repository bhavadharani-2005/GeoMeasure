import { ChevronLeft, ChevronRight, Crosshair, Ruler } from "lucide-react";
import { useEffect, useState } from "react";
import type { FeatureMeasurement } from "../../types/api";
import { formatNumber, formatPropertyValue, visibleProperties, friendlyMeasurement } from "../../utils/format";
import { EmptyState } from "../ui/EmptyState";

const PAGE_SIZE = 25;
const PREVIEW_ATTRIBUTES = 3;

interface Props {
  features: FeatureMeasurement[];
  selectedIndex: number | null;
  onSelect: (featureIndex: number) => void;
}

export function FeatureTable({ features, selectedIndex, onSelect }: Props) {
  const [page, setPage] = useState(0);
  const pageCount = Math.max(1, Math.ceil(features.length / PAGE_SIZE));

  // Jump to the page holding a feature selected from the map.
  useEffect(() => {
    if (selectedIndex === null) return;
    const position = features.findIndex((f) => f.feature_index === selectedIndex);
    if (position >= 0) setPage(Math.floor(position / PAGE_SIZE));
  }, [selectedIndex, features]);

  if (features.length === 0) {
    return (
      <EmptyState icon={Ruler} title="No measurements">
        This dataset has no features to measure.
      </EmptyState>
    );
  }

  const rows = features.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <>
      <div className="table-wrap">
        <table className="table table--dense">
          <thead>
            <tr>
              <th className="num">#</th>
              <th>Geometry</th>
              <th className="num">Measurement</th>
              <th>Unit</th>
              <th>Attributes</th>
              <th className="actions-col">
                <span className="sr-only">Details</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => {
              const entries = visibleProperties(f.properties);
              const extra = f.measurement ? friendlyMeasurement(f.measurement) : null;
              return (
                <tr
                  key={f.feature_index}
                  className={f.feature_index === selectedIndex ? "row--selected" : undefined}
                  onClick={() => onSelect(f.feature_index)}
                >
                  <td className="num muted">{f.feature_index}</td>
                  <td>{f.geometry_type}</td>
                  <td className="num">
                    {f.measurement ? (
                      <>
                        {formatNumber(f.measurement.value)}
                        {extra && <span className="muted subvalue"> ≈ {extra}</span>}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>{f.measurement?.unit ?? "—"}</td>
                  <td>
                    {entries.length === 0 ? (
                      <span className="muted">None</span>
                    ) : (
                      <span className="chips">
                        {entries.slice(0, PREVIEW_ATTRIBUTES).map(([k, v]) => (
                          <span key={k} className="chip" title={`${k}: ${formatPropertyValue(v)}`}>
                            <span className="chip__key">{k}</span>
                            <span className="truncate">{formatPropertyValue(v)}</span>
                          </span>
                        ))}
                        {entries.length > PREVIEW_ATTRIBUTES && (
                          <span className="muted">+{entries.length - PREVIEW_ATTRIBUTES}</span>
                        )}
                      </span>
                    )}
                  </td>
                  <td className="actions-col">
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(f.feature_index);
                      }}
                      aria-label={`Inspect feature ${f.feature_index}`}
                    >
                      <Crosshair size={14} aria-hidden="true" /> Inspect
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {pageCount > 1 && (
        <div className="pager">
          <span className="muted">
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, features.length)} of {features.length}
          </span>
          <span className="inline-actions">
            <button type="button" className="btn btn--ghost btn--icon" disabled={page === 0} onClick={() => setPage(page - 1)} aria-label="Previous page">
              <ChevronLeft size={18} />
            </button>
            <button type="button" className="btn btn--ghost btn--icon" disabled={page >= pageCount - 1} onClick={() => setPage(page + 1)} aria-label="Next page">
              <ChevronRight size={18} />
            </button>
          </span>
        </div>
      )}
    </>
  );
}
