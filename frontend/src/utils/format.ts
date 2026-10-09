import type { FeatureMeasurement, Measurement } from "../types/api";

const numberFormat = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
const intFormat = new Intl.NumberFormat("en-US");

export const formatInt = (n: number) => intFormat.format(n);
export const formatNumber = (n: number) => numberFormat.format(n);

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/** Friendly secondary unit for large canonical values (the API value stays in m² / m). */
export function friendlyMeasurement(m: Measurement): string | null {
  if (m.type === "area") {
    if (m.value >= 1_000_000) return `${formatNumber(m.value / 1_000_000)} km²`;
    if (m.value >= 10_000) return `${formatNumber(m.value / 10_000)} ha`;
  } else if (m.value >= 1000) {
    return `${formatNumber(m.value / 1000)} km`;
  }
  return null;
}

const STATUS_NOTES: Record<FeatureMeasurement["measurement_status"], string> = {
  MEASURED: "",
  NOT_APPLICABLE: "No measurement for this geometry",
  UNSUPPORTED: "Geometry type not supported for measurement",
  EMPTY: "Empty or missing geometry",
};
export const measurementNote = (status: FeatureMeasurement["measurement_status"]) => STATUS_NOTES[status];

export function formatPropertyValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export const FILE_TYPE_LABEL = { kml: "KML", shapefile: "Shapefile" } as const;

// Fields the GDAL KML driver adds to every feature; they are not user data.
const KML_DRIVER_FIELDS = new Set([
  "timestamp", "begin", "end", "altitudeMode", "tessellate", "extrude", "visibility", "drawOrder", "icon",
]);

/** Attributes worth showing: drops empty values and KML driver boilerplate (still returned by the API). */
export function visibleProperties(properties: Record<string, unknown>): [string, unknown][] {
  return Object.entries(properties).filter(
    ([key, v]) => v !== null && v !== undefined && v !== "" && !KML_DRIVER_FIELDS.has(key),
  );
}
