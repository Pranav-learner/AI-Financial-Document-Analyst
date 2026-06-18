/**
 * Enhanced API client with typed error handling, request cancellation,
 * and convenience methods for all HTTP verbs.
 *
 * All feature-specific services build on this foundation.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

/** Structured API error for consistent error handling across the app. */
export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let code = "UNKNOWN";
    let message = res.statusText;
    let details: Record<string, unknown> = {};

    try {
      const body = await res.json();
      if (body?.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
        details = body.error.details ?? {};
      }
    } catch {
      // Non-JSON error body — use defaults
    }

    throw new ApiError(res.status, code, message, details);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;
}

function buildHeaders(custom?: HeadersInit): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(custom ?? {}),
  };
}

/** Core request helper — all service methods delegate to this. */
export async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: buildHeaders(init?.headers),
    ...init,
  });
  return handleResponse<T>(res);
}

/** GET helper */
export function get<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>(path, { method: "GET", signal });
}

/** POST helper */
export function post<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body != null ? JSON.stringify(body) : undefined,
    signal,
  });
}

/** Operational helper used by the foundation App to prove connectivity. */
export function getHealth(): Promise<{ status: string }> {
  return get<{ status: string }>("/health");
}
