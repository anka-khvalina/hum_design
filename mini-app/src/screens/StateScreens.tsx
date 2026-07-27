import { ru } from "../i18n/ru";
import type { AppError } from "../types";

interface ExpiredScreenProps {
  onRestart: () => void;
}

interface AuthErrorScreenProps {
  error?: AppError;
  onRetry: () => void;
}

export function ExpiredScreen({ onRestart }: ExpiredScreenProps) {
  return (
    <section className="screen state-screen">
      <div className="state-symbol" aria-hidden="true">
        ◌
      </div>
      <h1>{ru.expired.title}</h1>
      <p className="muted">{ru.expired.message}</p>
      <div className="bottom-cta">
        <button className="button button--primary" type="button" onClick={onRestart}>
          {ru.expired.cta}
        </button>
      </div>
    </section>
  );
}

export function AuthErrorScreen({ error, onRetry }: AuthErrorScreenProps) {
  return (
    <section className="screen state-screen">
      <div className="state-symbol state-symbol--warning" aria-hidden="true">
        !
      </div>
      <h1>{error?.title ?? ru.authError.title}</h1>
      <p className="muted">{error?.message ?? ru.authError.message}</p>
      <div className="bottom-cta">
        <button className="button button--primary" type="button" onClick={onRetry}>
          {ru.authError.retry}
        </button>
      </div>
    </section>
  );
}
