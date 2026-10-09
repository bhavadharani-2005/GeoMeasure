import axios, { AxiosError } from "axios";
import type { ApiErrorBody } from "../types/api";

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const http = axios.create({ baseURL: API_BASE_URL, timeout: 120_000 });

/** An error whose message is safe to show to users. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof AxiosError) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body?.error) return new ApiError(body.error.message, body.error.code, error.response?.status);
    if (!error.response) {
      return new ApiError(
        "Cannot reach the GeoMeasure API. Check that the backend is running.",
        "NETWORK_ERROR",
      );
    }
    return new ApiError(`Request failed (${error.response.status}).`, "HTTP_ERROR", error.response.status);
  }
  return new ApiError("Something went wrong.", "UNKNOWN");
}

http.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(toApiError(error)),
);
