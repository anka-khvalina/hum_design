import { Component, type ErrorInfo, type ReactNode } from "react";
import { ru } from "../i18n/ru";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    hasError: false
  };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Mini App error boundary caught an error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="app-shell app-shell--center">
          <section className="panel error-panel">
            <p className="eyebrow">Human Design</p>
            <h1>{ru.errors.generic}</h1>
            <p>Обновите Mini App или вернитесь к началу демо.</p>
            <button className="button button--primary" onClick={() => window.location.reload()}>
              Обновить
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
