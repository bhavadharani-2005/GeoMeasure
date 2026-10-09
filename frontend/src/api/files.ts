import { http } from "./client";
import type {
  FeatureCollection,
  GeospatialFile,
  GeospatialFileDetail,
  Health,
  MeasurementsResponse,
  Stats,
  UploadResponse,
} from "../types/api";

export const filesApi = {
  upload: (file: File, signal?: AbortSignal) => {
    const form = new FormData();
    form.append("file", file);
    return http.post<UploadResponse>("/api/files/", form, { signal }).then((r) => r.data);
  },
  list: (limit = 100) =>
    http.get<GeospatialFile[]>("/api/files/", { params: { limit } }).then((r) => r.data),
  get: (id: string) => http.get<GeospatialFileDetail>(`/api/files/${id}/`).then((r) => r.data),
  measurements: (id: string) =>
    http.get<MeasurementsResponse>(`/api/files/${id}/measurements/`).then((r) => r.data),
  geojson: (id: string) => http.get<FeatureCollection>(`/api/files/${id}/geojson/`).then((r) => r.data),
  remove: (id: string) => http.delete(`/api/files/${id}/`).then(() => undefined),
  stats: () => http.get<Stats>("/api/stats/").then((r) => r.data),
  health: () => http.get<Health>("/api/health/", { timeout: 5000 }).then((r) => r.data),
};
