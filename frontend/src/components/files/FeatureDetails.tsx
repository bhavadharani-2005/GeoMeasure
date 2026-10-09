import { MousePointerClick } from "lucide-react";
import type { FeatureMeasurement } from "../../types/api";
import { formatNumber, formatPropertyValue, visibleProperties, friendlyMeasurement, measurementNote } from "../../utils/format";
import { EmptyState } from "../ui/EmptyState";

export function FeatureDetails({ feature }: { feature: FeatureMeasurement | null }) {
  if (!feature) {
    return (
      <EmptyState icon={MousePointerClick} title="No feature selected" compact>
        Click a feature on the map or a row in the table to inspect it.
      </EmptyState>
    );
  }
  const entries = visibleProperties(feature.properties);
  const m = feature.measurement;
  const friendly = m ? friendlyMeasurement(m) : null;

  return (
    <div className="stack">
      <dl className="kv">
        <div className="kv__row">
          <dt>Feature</dt>
          <dd>#{feature.feature_index}</dd>
        </div>
        <div className="kv__row">
          <dt>Geometry</dt>
          <dd>{feature.geometry_type}</dd>
        </div>
        <div className="kv__row">
          <dt>CRS</dt>
          <dd>{feature.crs ?? "—"}</dd>
        </div>
        <div className="kv__row">
          <dt>{m ? (m.type === "area" ? "Area" : "Length") : "Measurement"}</dt>
          <dd>
            {m ? (
              <>
                {formatNumber(m.value)} {m.unit}
                {friendly && <span className="muted"> ≈ {friendly}</span>}
              </>
            ) : (
              <span className="muted">{measurementNote(feature.measurement_status) || "—"}</span>
            )}
          </dd>
        </div>
      </dl>
      <div>
        <h3 className="subhead">Attributes</h3>
        {entries.length === 0 ? (
          <p className="muted">This feature has no attributes.</p>
        ) : (
          <dl className="kv kv--scroll">
            {entries.map(([key, value]) => (
              <div className="kv__row" key={key}>
                <dt>{key}</dt>
                <dd>{formatPropertyValue(value)}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}
