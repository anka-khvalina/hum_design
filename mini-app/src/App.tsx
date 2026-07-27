import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClient, ApiError } from "./api/client";
import { DemoModeBadge } from "./components/DemoModeBadge";
import { ru } from "./i18n/ru";
import { AnswerScreen } from "./screens/AnswerScreen";
import { CalculatingScreen } from "./screens/CalculatingScreen";
import { ConfirmScreen } from "./screens/ConfirmScreen";
import { FormScreen } from "./screens/FormScreen";
import { ResultScreen } from "./screens/ResultScreen";
import { AuthErrorScreen, ExpiredScreen } from "./screens/StateScreens";
import { WelcomeScreen } from "./screens/WelcomeScreen";
import type {
  AppError,
  BirthFormData,
  BodygraphResponse,
  DemoMode,
  QuestionAnswer,
  QuestionKey,
  Screen
} from "./types";

const emptyFormData: BirthFormData = {
  name: "",
  birthDate: "",
  birthTime: "",
  locationQuery: "",
  location: null
};

export function App() {
  const api = useMemo(() => new ApiClient(), []);
  const imageUrlRef = useRef("");
  const [screen, setScreen] = useState<Screen>("welcome");
  const [authLoading, setAuthLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [demoMode, setDemoMode] = useState<DemoMode>();
  const [formData, setFormData] = useState<BirthFormData>(emptyFormData);
  const [result, setResult] = useState<BodygraphResponse | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [answer, setAnswer] = useState<QuestionAnswer | null>(null);
  const [appError, setAppError] = useState<AppError>();

  const authenticate = useCallback(async () => {
    setAuthLoading(true);
    setAppError(undefined);

    try {
      const telegramApp = window.Telegram?.WebApp;
      telegramApp?.ready();
      telegramApp?.expand();

      const initData = telegramApp?.initData?.trim() || "demo:local";
      const authResponse = await api.authenticate(initData);
      setDemoMode(authResponse.demoMode);
      setScreen((current) => (current === "authError" ? "welcome" : current));
    } catch {
      setAppError({
        title: ru.authError.title,
        message: ru.authError.message,
        canRetry: true
      });
      setScreen("authError");
    } finally {
      setAuthLoading(false);
    }
  }, [api]);

  useEffect(() => {
    void authenticate();
  }, [authenticate]);

  useEffect(() => {
    return () => {
      if (imageUrlRef.current) {
        URL.revokeObjectURL(imageUrlRef.current);
      }
    };
  }, []);

  const searchLocations = useCallback(
    (query: string, signal?: AbortSignal) => api.searchLocations(query, signal),
    [api]
  );

  function handleFormSubmit(data: BirthFormData) {
    setFormData(data);
    setScreen("confirm");
  }

  async function buildBodygraph() {
    if (isSubmitting) {
      return;
    }

    if (!formData.location) {
      setScreen("form");
      return;
    }

    setIsSubmitting(true);
    setAppError(undefined);
    setScreen("calculating");

    try {
      const loc = formData.location;
      if (
        !loc.name ||
        !loc.country ||
        !loc.timezone ||
        loc.latitude == null ||
        loc.longitude == null
      ) {
        throw new ApiError("Выберите место рождения из списка", 422);
      }

      const createdResult = await api.createBodygraph({
        name: formData.name,
        birthDate: formData.birthDate,
        birthTime: formData.birthTime,
        location: {
          name: loc.name,
          region: loc.region,
          country: loc.country,
          timezone: loc.timezone,
          latitude: loc.latitude,
          longitude: loc.longitude
        }
      });
      const nextImageUrl = await api.fetchBodygraphImage(createdResult.sessionId);

      if (imageUrlRef.current) {
        URL.revokeObjectURL(imageUrlRef.current);
      }

      imageUrlRef.current = nextImageUrl;
      setResult(createdResult);
      if (createdResult.demoMode) {
        setDemoMode(
          createdResult.demoMode === "fixture" || createdResult.demoMode === "DEMO FALLBACK"
            ? "DEMO FALLBACK"
            : "LIVE"
        );
      }
      setImageUrl(nextImageUrl);
      setScreen("result");
    } catch (error) {
      routeApiError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function askQuestion(type: QuestionKey, question?: string): Promise<QuestionAnswer> {
    if (!result) {
      throw new ApiError(ru.errors.sessionExpired, 410);
    }

    try {
      return await api.askQuestion(result.sessionId, type, question);
    } catch (error) {
      routeApiError(error);
      throw error;
    }
  }

  async function sendToTelegram() {
    if (!result) {
      throw new ApiError(ru.errors.sessionExpired, 410);
    }

    try {
      await api.sendToTelegram(result.sessionId);
    } catch (error) {
      routeApiError(error);
      throw error;
    }
  }

  function routeApiError(error: unknown) {
    if (error instanceof ApiError) {
      if (error.status === 401 || error.status === 403) {
        setAppError({
          title: ru.authError.title,
          message: ru.authError.message,
          canRetry: true
        });
        setScreen("authError");
        return;
      }

      if (error.status === 404 || error.status === 410) {
        setScreen("expired");
        return;
      }

      setAppError({
        title: "Не удалось выполнить запрос",
        message: error.message || ru.errors.generic,
        canRetry: true
      });
      setScreen("authError");
      return;
    }

    setAppError({
      title: "Не удалось выполнить запрос",
      message: ru.errors.generic,
      canRetry: true
    });
    setScreen("authError");
  }

  function restartFlow() {
    setFormData(emptyFormData);
    setResult(null);
    setAnswer(null);
    setAppError(undefined);
    setScreen("form");

    if (imageUrlRef.current) {
      URL.revokeObjectURL(imageUrlRef.current);
      imageUrlRef.current = "";
      setImageUrl("");
    }
  }

  return (
    <main className="app-shell">
      <div className="ambient ambient--violet" aria-hidden="true" />
      <div className="ambient ambient--gold" aria-hidden="true" />
      <DemoModeBadge mode={demoMode} />
      <div className="phone-stage">{renderScreen()}</div>
    </main>
  );

  function renderScreen() {
    switch (screen) {
      case "welcome":
        return (
          <WelcomeScreen
            authLoading={authLoading}
            onStart={() => setScreen(authLoading ? "welcome" : "form")}
          />
        );
      case "form":
        return (
          <FormScreen
            initialData={formData}
            onSubmit={handleFormSubmit}
            searchLocations={searchLocations}
          />
        );
      case "confirm":
        return (
          <ConfirmScreen
            data={formData}
            isSubmitting={isSubmitting}
            onEdit={() => setScreen("form")}
            onBuild={() => void buildBodygraph()}
          />
        );
      case "calculating":
        return <CalculatingScreen />;
      case "result":
        return result && imageUrl ? (
          <ResultScreen
            result={result}
            imageUrl={imageUrl}
            onAskQuestion={askQuestion}
            onAnswer={(nextAnswer) => {
              setAnswer(nextAnswer);
              setScreen("answer");
            }}
            onSendToTelegram={sendToTelegram}
          />
        ) : (
          <ExpiredScreen onRestart={restartFlow} />
        );
      case "answer":
        return answer ? (
          <AnswerScreen answer={answer} onBack={() => setScreen("result")} />
        ) : (
          <ExpiredScreen onRestart={restartFlow} />
        );
      case "expired":
        return <ExpiredScreen onRestart={restartFlow} />;
      case "authError":
        return <AuthErrorScreen error={appError} onRetry={() => void authenticate()} />;
      default:
        return null;
    }
  }
}
