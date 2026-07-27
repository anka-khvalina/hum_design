import { useMemo, useState } from "react";
import { BodygraphImage } from "../components/BodygraphImage";
import { questionLabels, ru } from "../i18n/ru";
import type { BodygraphResponse, QuestionAnswer, QuestionKey } from "../types";

interface ResultScreenProps {
  result: BodygraphResponse;
  imageUrl: string;
  onAskQuestion: (type: QuestionKey, question?: string) => Promise<QuestionAnswer>;
  onAnswer: (answer: QuestionAnswer) => void;
  onSendToTelegram: () => Promise<void>;
}

const presetQuestions: QuestionKey[] = [
  "talents",
  "direction",
  "work",
  "money",
  "character",
  "relationships",
  "energy",
  "custom"
];

export function ResultScreen({
  result,
  imageUrl,
  onAskQuestion,
  onAnswer,
  onSendToTelegram
}: ResultScreenProps) {
  const [expandedDetails, setExpandedDetails] = useState(false);
  const [customOpen, setCustomOpen] = useState(false);
  const [customQuestion, setCustomQuestion] = useState("");
  const [loadingQuestion, setLoadingQuestion] = useState<QuestionKey | null>(null);
  const [questionError, setQuestionError] = useState("");
  const [sendState, setSendState] = useState<"idle" | "sending" | "sent">("idle");

  const params = useMemo(
    () => [
      ["Тип", result.type],
      ["Стратегия", result.strategy],
      ["Авторитет", result.authority],
      ["Профиль", result.profile],
      ["Определенность", result.definition],
      ["Дело жизни", result.lifeWork]
    ],
    [result]
  );

  async function ask(type: QuestionKey, question?: string) {
    if (type === "custom" && !question?.trim()) {
      setCustomOpen(true);
      return;
    }

    setLoadingQuestion(type);
    setQuestionError("");

    try {
      const answer = await onAskQuestion(type, question?.trim());
      onAnswer(answer);
    } catch {
      setQuestionError(ru.errors.generic);
    } finally {
      setLoadingQuestion(null);
    }
  }

  async function sendToTelegram() {
    setSendState("sending");
    try {
      await onSendToTelegram();
      setSendState("sent");
    } catch {
      setSendState("idle");
      setQuestionError(ru.errors.generic);
    }
  }

  return (
    <section className="screen result-screen">
      <p className="eyebrow">{ru.brand}</p>
      <h1>{result.title || ru.result.titleFallback}</h1>
      <p className="result-name">{result.name}</p>

      <BodygraphImage imageUrl={imageUrl} />

      <div className="panel summary-card">
        <h2>{ru.result.mainParams}</h2>
        <div className="params-grid">
          {params.map(([label, value]) => (
            <div className="param-pill" key={label}>
              <span>{label}</span>
              <strong>{value || "—"}</strong>
            </div>
          ))}
        </div>
        <p>{result.summary}</p>
        {expandedDetails ? (
          <div className="details-card">
            {[
              ["Подпись", result.details?.signature],
              ["Тема ложного «Я»", result.details?.notSelfTheme],
              ["Инкарнационный крест", result.details?.incarnationCross],
              ["Cognition", result.details?.cognition],
              ["Determination", result.details?.determination],
              ["Variables", result.details?.variables],
              ["Motivation", result.details?.motivation],
              ["Perspective", result.details?.perspective],
              ["Environment", result.details?.environment]
            ].map(([label, value]) =>
              value ? (
                <p key={String(label)}>
                  <strong>{label}:</strong> {String(value)}
                </p>
              ) : null
            )}
            {Array.isArray(result.details?.centers) && result.details.centers.length > 0 ? (
              <p>
                <strong>Центры:</strong> {result.details.centers.join(", ")}
              </p>
            ) : null}
            {Array.isArray(result.details?.channels) && result.details.channels.length > 0 ? (
              <p>
                <strong>Каналы:</strong> {result.details.channels.join(", ")}
              </p>
            ) : null}
            {Array.isArray(result.details?.gates) && result.details.gates.length > 0 ? (
              <p>
                <strong>Ворота:</strong> {result.details.gates.join(", ")}
              </p>
            ) : null}
            <p className="muted">Часовой пояс расчета: {result.timezone || "уточняется"}</p>
          </div>
        ) : null}
        <button
          className="link-button"
          type="button"
          onClick={() => setExpandedDetails((current) => !current)}
        >
          {ru.result.details}
        </button>
      </div>

      <div className="question-section">
        <h2>{ru.result.questionsTitle}</h2>
        <div className="question-grid">
          {presetQuestions.map((type) => (
            <button
              className="question-button"
              key={type}
              type="button"
              disabled={Boolean(loadingQuestion)}
              onClick={() => {
                if (type === "custom") {
                  setCustomOpen(true);
                } else {
                  void ask(type);
                }
              }}
            >
              {loadingQuestion === type ? "Готовим ответ..." : questionLabels[type]}
            </button>
          ))}
        </div>

        {customOpen ? (
          <form
            className="custom-question"
            onSubmit={(event) => {
              event.preventDefault();
              void ask("custom", customQuestion);
            }}
          >
            <textarea
              rows={3}
              value={customQuestion}
              placeholder={ru.result.customPlaceholder}
              onChange={(event) => setCustomQuestion(event.target.value)}
            />
            <button className="button button--secondary" disabled={Boolean(loadingQuestion)}>
              {loadingQuestion === "custom" ? "Готовим ответ..." : ru.result.askCustom}
            </button>
          </form>
        ) : null}
        {questionError ? <p className="field-error">{questionError}</p> : null}
      </div>

      <div className="bottom-cta">
        <button
          className="button button--primary"
          type="button"
          disabled={sendState === "sending" || sendState === "sent"}
          onClick={() => void sendToTelegram()}
        >
          {sendState === "sent"
            ? ru.result.sent
            : sendState === "sending"
              ? ru.result.sending
              : ru.result.send}
        </button>
      </div>
    </section>
  );
}
