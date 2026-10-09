export type FileStatus = "PROCESSING" | "COMPLETED" | "FAILED";
export type FileType = "kml" | "shapefile";
export type MeasurementStatus = "MEASURED" | "NOT_APPLICABLE" | "UNSUPPORTED" | "EMPTY";

export interface GeospatialFile {
  id: string;
  filename: string;
  file_type: FileType;
  file_size: number;
  feature_count: number;
  original_crs: string | null;
  projected_crs: string | null;
  crs: string | null;
  status: FileStatus;
  error_message: string | null;
  created_at: string;
  geometry_summary: Record<string, number>;
}

export interface GeospatialFileDetail extends GeospatialFile {
  updated_at: string;
}

export interface UploadResponse {
  id: string;
  filename: string;
  original_crs: string | null;
  feature_count: number;
  status: FileStatus;
  created_at: string;
}

export interface Measurement {
  type: "area" | "length";
  value: number;
  unit: string;
}

export type Properties = Record<string, unknown>;

export interface FeatureMeasurement {
  feature_index: number;
  geometry_type: string;
  geometry: GeoJSON.Geometry | null;
  crs: string | null;
  properties: Properties;
  measurement: Measurement | null;
  measurement_status: MeasurementStatus;
}

export interface MeasurementsResponse {
  file_id: string;
  original_crs: string | null;
  projected_crs: string | null;
  geometry_crs: string;
  feature_count: number;
  features: FeatureMeasurement[];
}

export interface FeatureGeoProperties {
  feature_index: number;
  geometry_type: string;
  measurement: Measurement | null;
  measurement_status: MeasurementStatus;
  attributes: Properties;
}

export type FeatureCollection = GeoJSON.FeatureCollection<GeoJSON.Geometry, FeatureGeoProperties>;

export interface Stats {
  files_total: number;
  files_completed: number;
  files_failed: number;
  features_total: number;
  geometry_counts: Record<string, number>;
}

export interface Health {
  status: string;
  database: string;
  version: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
}
