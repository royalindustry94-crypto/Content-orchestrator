import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
  /**
   * When any value in this array changes, the boundary clears its error and
   * attempts to render its children again. Used to auto-recover on navigation.
   */
  resetKeys?: ReadonlyArray<unknown>;
  /** Render prop for the fallback UI. Receives the error and a manual reset. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** Optional label used in the default fallback copy. */
  title?: string;
};

type State = {
  error: Error | null;
};

function areKeysEqual(a: ReadonlyArray<unknown>, b: ReadonlyArray<unknown>): boolean {
  if (a.length !== b.length) return false;
  return a.every((value, index) => Object.is(value, b[index]));
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(prevProps: Props) {
    const prev = prevProps.resetKeys ?? [];
    const next = this.props.resetKeys ?? [];
    if (this.state.error && !areKeysEqual(prev, next)) {
      this.setState({ error: null });
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface the failure for observability instead of swallowing it silently.
    console.error("UI ErrorBoundary caught an error", error, info.componentStack);
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    if (error) {
      if (this.props.fallback) {
        return this.props.fallback(error, this.reset);
      }
      return (
        <div className="error-state" role="alert">
          <h3>{this.props.title ?? "Something went wrong"}</h3>
          <p>{error.message || "An unexpected error occurred while rendering this screen."}</p>
          <button className="button button--primary" onClick={this.reset} type="button">
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
