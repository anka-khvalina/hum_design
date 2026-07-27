import type {
  AuthResponse,
  BodygraphRequest,
  BodygraphResponse,
  LocationSuggestion,
  QuestionAnswer,
  QuestionKey
} from "../types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class ApiClient {
  private readonly baseUrl: string;
  private accessToken = "";

  constructor(baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  setAccessToken(accessToken: string) {
    this.accessToken = accessToken;
  }

  async authenticate(initData: string): Promise<AuthResponse> {
    const response = await this.request<unknown>("/api/v1/auth/telegram", {
      method: "POST",
      body: JSON.stringify({ initData }),
      auth: false
    });
    const data = response as Record<string, unknown>;
    const accessToken = String(data.accessToken ?? data.access_token ?? "");

    if (!accessToken) {
      throw new ApiError("Auth response does not include accessToken", 401);
    }

    this.setAccessToken(accessToken);

    return {
      accessToken,
      demoMode:
        typeof data.demoMode === "string"
          ? data.demoMode
          : typeof data.demo_mode === "string"
            ? data.demo_mode
            : undefined
    };
  }

  async searchLocations(query: string, signal?: AbortSignal): Promise<LocationSuggestion[]> {
    const data = await this.request<unknown>(
      `/api/v1/locations?query=${encodeURIComponent(query)}`,
      { method: "GET", signal }
    );
    const container = data as Record<string, unknown>;
    const rawItems: unknown[] = Array.isArray(data)
      ? data
      : Array.isArray(container.items)
        ? container.items
        : Array.isArray(container.locations)
          ? container.locations
          : [];

    return rawItems
      .map((item) => normalizeLocation(item as Record<string, unknown>))
      .filter((location): location is LocationSuggestion => Boolean(location));
  }

  async createBodygraph(payload: BodygraphRequest): Promise<BodygraphResponse> {
    const response = await this.request<unknown>("/api/v1/bodygraphs", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    return normalizeBodygraph(response as Record<string, unknown>);
  }

  async fetchBodygraphImage(sessionId: string): Promise<string> {
    const response = await fetch(
      `${this.baseUrl}/api/v1/demo-sessions/${encodeURIComponent(sessionId)}/image`,
      {
        headers: this.authHeaders()
      }
    );

    if (!response.ok) {
      throw await toApiError(response);
    }

    const blob = await response.blob();
    return URL.createObjectURL(blob);
  }

  async askQuestion(
    sessionId: string,
    questionType: QuestionKey,
    question?: string
  ): Promise<QuestionAnswer> {
    const data = await this.request<unknown>(
      `/api/v1/demo-sessions/${encodeURIComponent(sessionId)}/questions`,
      {
        method: "POST",
        body: JSON.stringify({ questionType, question })
      }
    );

    return normalizeAnswer(data as Record<string, unknown>, questionType, question);
  }

  async sendToTelegram(sessionId: string): Promise<void> {
    await this.request<unknown>(
      `/api/v1/demo-sessions/${encodeURIComponent(sessionId)}/send-to-telegram`,
      {
        method: "POST"
      }
    );
  }

  private async request<T>(
    path: string,
    options: RequestInit & { auth?: boolean } = {}
  ): Promise<T> {
    const { auth = true, headers, ...requestOptions } = options;
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...requestOptions,
      headers: {
        "Content-Type": "application/json",
        ...(auth ? this.authHeaders() : {}),
        ...headers
      }
    });

    if (!response.ok) {
      throw await toApiError(response);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  private authHeaders(): HeadersInit {
    if (!this.accessToken) {
      return {};
    }

    return {
      Authorization: `Bearer ${this.accessToken}`
    };
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let message = response.statusText || "Request failed";

  try {
    const data = (await response.json()) as Record<string, unknown>;
    if (typeof data.detail === "string") {
      message = data.detail;
    } else if (typeof data.message === "string") {
      message = data.message;
    }
  } catch {
    // Non-JSON error bodies are expected for some proxy and auth failures.
  }

  return new ApiError(message, response.status);
}

function normalizeLocation(item: Record<string, unknown>): LocationSuggestion | null {
  const id = String(item.id ?? item.placeId ?? item.place_id ?? item.geonameId ?? "");
  const label = String(
    item.label ??
      item.displayName ??
      item.display_name ??
      item.fullName ??
      item.full_name ??
      item.name ??
      ""
  );

  if (!id || !label) {
    return null;
  }

  return {
    id,
    label,
    name: optionalString(item.name),
    country: optionalString(item.country),
    region: optionalString(item.region),
    timezone: optionalString(item.timezone ?? item.timeZone ?? item.time_zone),
    latitude: optionalNumber(item.latitude ?? item.lat),
    longitude: optionalNumber(item.longitude ?? item.lon ?? item.lng)
  };
}

function normalizeBodygraph(data: Record<string, unknown>): BodygraphResponse {
  const sessionId = String(data.sessionId ?? data.session_id ?? data.id ?? "");
  if (!sessionId) {
    throw new ApiError("Bodygraph response does not include sessionId", 500);
  }

  const params = (data.params ?? data.mainParams ?? data.main_params ?? data) as Record<
    string,
    unknown
  >;

  return {
    sessionId,
    name: String(data.name ?? params.name ?? ""),
    timezone: String(data.timezone ?? data.timeZone ?? data.time_zone ?? ""),
    title: optionalString(data.title ?? data.emotionalTitle ?? data.emotional_title),
    summary: String(data.summary ?? data.shortSummary ?? data.short_summary ?? ""),
    type: String(params.type ?? params.hdType ?? params.hd_type ?? data.type ?? ""),
    strategy: String(params.strategy ?? data.strategy ?? ""),
    authority: String(params.authority ?? data.authority ?? ""),
    profile: String(params.profile ?? data.profile ?? ""),
    definition: String(params.definition ?? data.definition ?? ""),
    lifeWork: String(
      params.lifeWork ??
        params.life_work ??
        params.incarnationCross ??
        params.incarnation_cross ??
        data.lifeWork ??
        data.life_work ??
        ""
    )
  };
}

function normalizeAnswer(
  data: Record<string, unknown>,
  fallbackType: QuestionKey,
  fallbackQuestion?: string
): QuestionAnswer {
  return {
    questionType: (data.questionType ?? data.question_type ?? fallbackType) as QuestionKey,
    question: optionalString(data.question ?? fallbackQuestion),
    shortAnswer: String(data.shortAnswer ?? data.short_answer ?? data.answer ?? ""),
    manifestations: normalizeStringList(data.manifestations),
    strength: String(data.strength ?? ""),
    attentionPoint: String(data.attentionPoint ?? data.attention_point ?? ""),
    basedOn: String(data.basedOn ?? data.based_on ?? ""),
    reflectionQuestion: String(data.reflectionQuestion ?? data.reflection_question ?? "")
  };
}

function normalizeStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(String).filter(Boolean);
  }

  if (typeof value === "string" && value.trim()) {
    return [value.trim()];
  }

  return [];
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function optionalNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }

  return undefined;
}
