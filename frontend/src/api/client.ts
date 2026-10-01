import type {
  Availability,
  AvailabilityUpdate,
  EmployeeProfile,
  PerformanceScore,
  ReviewCycle,
  TokenResponse,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  token?: string;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, headers, ...rest } = options;
  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    // The backend's exception handlers guarantee a safe, generic {detail}
    // body (see backend/app/main.py) — never a raw stack trace.
    let message = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // non-JSON error body; fall back to statusText
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  devLogin: (employeeId: number) =>
    request<TokenResponse>("/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ employee_id: employeeId }),
    }),
  getMyProfile: (token: string) => request<EmployeeProfile>("/employees/me", { token }),
  getMyAvailability: (token: string) => request<Availability>("/employees/me/availability", { token }),
  updateMyAvailability: (token: string, payload: AvailabilityUpdate) =>
    request<Availability>("/employees/me/availability", {
      method: "PATCH",
      token,
      body: JSON.stringify(payload),
    }),
  getCurrentCycle: (token: string) => request<ReviewCycle>("/cycles/current", { token }),
  getMyScores: (token: string, cycleId?: number) =>
    request<PerformanceScore[]>(`/employees/me/scores${cycleId ? `?cycle_id=${cycleId}` : ""}`, { token }),
};
