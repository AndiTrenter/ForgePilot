import React from "react";

/**
 * Globaler ErrorBoundary.
 *
 * Schutzschild gegen "schwarzer Screen": fängt jeden ungefangenen Render-Fehler
 * im Sub-Tree und zeigt einen lesbaren Fallback statt den ganzen App-Tree zu killen.
 *
 * Nutze ihn so weit oben wie möglich (App-Root) UND bei kritischen Sub-Bäumen
 * (Chat, Preview) – damit ein Crash in einem Panel nicht die ganze UI mitnimmt.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary]", this.props.label || "root", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (typeof this.props.onReset === "function") {
      this.props.onReset();
    }
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (typeof this.props.fallback === "function") {
      return this.props.fallback({
        error: this.state.error,
        errorInfo: this.state.errorInfo,
        reset: this.handleReset,
      });
    }

    const message =
      (this.state.error && (this.state.error.message || String(this.state.error))) ||
      "Unbekannter Fehler.";

    return (
      <div className="min-h-[200px] w-full flex items-center justify-center bg-zinc-950 text-zinc-200 p-6">
        <div className="max-w-xl w-full border border-rose-500/30 bg-rose-500/5 rounded-lg p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="inline-block w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            <h2 className="text-base font-semibold text-rose-300">
              {this.props.label
                ? `Fehler in: ${this.props.label}`
                : "Etwas ist schiefgelaufen"}
            </h2>
          </div>
          <p className="text-sm text-zinc-400 mb-4">
            Der UI-Bereich konnte nicht gerendert werden. Deine Eingaben sind nicht
            verloren – versuche zuerst „Erneut versuchen". Wenn das Problem bleibt,
            lade die Seite neu.
          </p>
          <pre className="text-xs bg-zinc-900 border border-zinc-800 rounded p-3 mb-4 overflow-x-auto whitespace-pre-wrap text-rose-200/80">
            {message}
          </pre>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={this.handleReset}
              className="px-3 py-1.5 text-sm rounded bg-white text-black hover:bg-zinc-200"
            >
              Erneut versuchen
            </button>
            <button
              type="button"
              onClick={this.handleReload}
              className="px-3 py-1.5 text-sm rounded border border-zinc-700 text-zinc-200 hover:bg-zinc-800"
            >
              Seite neu laden
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
