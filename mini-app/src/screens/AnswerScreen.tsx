import { questionLabels, ru } from "../i18n/ru";
import type { QuestionAnswer } from "../types";

interface AnswerScreenProps {
  answer: QuestionAnswer;
  onBack: () => void;
}

export function AnswerScreen({ answer, onBack }: AnswerScreenProps) {
  return (
    <section className="screen answer-screen">
      <p className="eyebrow">{ru.brand}</p>
      <h1>{answer.question ? answer.question : questionLabels[answer.questionType]}</h1>

      <div className="panel answer-card">
        <p className="answer-short">{answer.shortAnswer}</p>

        <section>
          <h2>{ru.answer.manifestations}</h2>
          <ul className="manifestation-list">
            {answer.manifestations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <div className="answer-grid">
          <InfoBlock title={ru.answer.strength} text={answer.strength} />
          <InfoBlock title={ru.answer.attentionPoint} text={answer.attentionPoint} />
          <InfoBlock
            title={ru.answer.basedOn}
            text={answer.basedOn.filter(Boolean).join("\n")}
          />
          <InfoBlock title={ru.answer.reflectionQuestion} text={answer.reflectionQuestion} />
        </div>
      </div>

      <div className="bottom-cta">
        <button className="button button--secondary" type="button" onClick={onBack}>
          {ru.answer.back}
        </button>
      </div>
    </section>
  );
}

function InfoBlock({ title, text }: { title: string; text: string }) {
  if (!text) {
    return null;
  }

  return (
    <section className="info-block">
      <h2>{title}</h2>
      {text.includes("\n") ? (
        <ul className="manifestation-list">
          {text
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line) => (
              <li key={line}>{line}</li>
            ))}
        </ul>
      ) : (
        <p>{text}</p>
      )}
    </section>
  );
}
