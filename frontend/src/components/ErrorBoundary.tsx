import React from "react";

type State = {
  error: Error | null;
};

type Props = {
  children: React.ReactNode;
};

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="page">
          <section className="error-panel">
            <h1>Что-то пошло не так</h1>
            <p>{this.state.error.message || "Интерфейс не смог отрисовать страницу."}</p>
            <button type="button" onClick={() => window.location.reload()}>
              Обновить страницу
            </button>
          </section>
        </div>
      );
    }

    return this.props.children;
  }
}
