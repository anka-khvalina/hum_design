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
        body: JSON.stringify({ category: questionType, question })
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
  const name = optionalString(item.name) || "";
  const region = optionalString(item.region);
  const country = optionalString(item.country) || "";
  const label = String(
    item.label ??
      item.displayName ??
      item.display_name ??
      [name, region, country].filter(Boolean).join(", ") ??
      name
  );

  if (!id || !label) {
    return null;
  }

  return {
    id,
    label,
    name: name || label,
    country,
    region,
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

  const chart = (data.bodygraph ?? data.params ?? data.mainParams ?? data) as Record<
    string,
    unknown
  >;
  const summaryObj = data.summary;
  const summaryText =
    typeof summaryObj === "string"
      ? summaryObj
      : summaryObj && typeof summaryObj === "object"
        ? String((summaryObj as Record<string, unknown>).text ?? "")
        : String(data.shortSummary ?? data.short_summary ?? "");
  const summaryTitle =
    summaryObj && typeof summaryObj === "object"
      ? optionalString((summaryObj as Record<string, unknown>).title)
      : optionalString(data.title ?? data.emotionalTitle);

  const birth = (data.birthData ?? data.birth_data ?? {}) as Record<string, unknown>;
  const location = (birth.location ?? {}) as Record<string, unknown>;

  return {
    sessionId,
    name: String(birth.name ?? data.name ?? ""),
    timezone: String(location.timezone ?? data.timezone ?? ""),
    title: summaryTitle,
    summary: summaryText,
    type: String(chart.type ?? data.type ?? ""),
    strategy: String(chart.strategy ?? data.strategy ?? ""),
    authority: String(chart.authority ?? data.authority ?? ""),
    profile: String(chart.profile ?? data.profile ?? ""),
    definition: String(chart.definition ?? data.definition ?? ""),
    lifeWork: String(
      chart.incarnationCross ??
        chart.incarnation_cross ??
        chart.lifeWork ??
        data.lifeWork ??
        ""
    ),
    demoMode: optionalString(data.demoMode ?? data.demo_mode),
    details: {
      signature: optionalString(chart.signature),
      notSelfTheme: optionalString(chart.notSelfTheme ?? chart.not_self_theme),
      incarnationCross: optionalString(chart.incarnationCross ?? chart.incarnation_cross),
      centers: Array.isArray(chart.centers) ? chart.centers.map(String) : undefined,
      channels: Array.isArray(chart.channels) ? chart.channels.map(String) : undefined,
      gates: Array.isArray(chart.gates) ? chart.gates.map(String) : undefined,
      cognition: optionalString(chart.cognition),
      determination: optionalString(chart.determination),
      variables: optionalString(chart.variables),
      motivation: optionalString(chart.motivation),
      perspective: optionalString(chart.perspective),
      environment: optionalString(chart.environment)
    }
  };
}

function normalizeAnswer(
  data: Record<string, unknown>,
  fallbackType: QuestionKey,
  fallbackQuestion?: string
): QuestionAnswer {
  const basedOnRaw = data.basedOn ?? data.based_on ?? data.usedChartElements;
  return {
    questionType: (data.questionType ?? data.question_type ?? data.category ?? fallbackType) as QuestionKey,
    question: optionalString(data.question ?? fallbackQuestion),
    title: optionalString(data.title),
    shortAnswer: String(data.shortAnswer ?? data.short_answer ?? data.answer ?? ""),
    manifestations: normalizeStringList(data.manifestations),
    strength: String(data.strength ?? ""),
    attentionPoint: String(data.attentionPoint ?? data.attention_point ?? ""),
    basedOn: normalizeStringList(basedOnRaw),
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
