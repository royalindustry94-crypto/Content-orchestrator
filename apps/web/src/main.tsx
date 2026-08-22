import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import ErrorBoundary from "./ErrorBoundary";
import "./app.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ErrorBoundary
      title="Lumora hit an unexpected error"
      fallback={(error, reset) => (
        <div className="app-crash" role="alert">
          <div>
            <h1>Lumora hit an unexpected error</h1>
            <p>{error.message || "The application encountered a problem and could not continue."}</p>
            <div className="app-crash__actions">
              <button className="button button--primary" onClick={reset} type="button">
                Try again
              </button>
              <button className="button button--ghost" onClick={() => window.location.reload()} type="button">
                Reload Lumora
              </button>
            </div>
          </div>
        </div>
      )}
    >
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
