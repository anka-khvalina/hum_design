import { ru } from "../i18n/ru";

interface WelcomeScreenProps {
  authLoading: boolean;
  onStart: () => void;
}

export function WelcomeScreen({ authLoading, onStart }: WelcomeScreenProps) {
  return (
    <section className="screen welcome-screen">
      <div className="hero-mark" aria-hidden="true">
        <span />
      </div>
      <p className="eyebrow">{ru.welcome.eyebrow}</p>
      <h1>{ru.brand}</h1>
      <p className="lead">{ru.welcome.title}</p>
      <p className="muted">{ru.welcome.text}</p>

      <div className="bottom-cta">
        <button className="button button--primary" disabled={authLoading} onClick={onStart}>
          {authLoading ? "Подключаем Telegram..." : ru.welcome.cta}
        </button>
      </div>
    </section>
  );
}
