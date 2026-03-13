"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("PRITHVINET error boundary caught:", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center bg-card p-8 rounded-lg border border-border max-w-lg">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-4" />
        <h2 className="text-lg font-bold text-foreground mb-2">
          Something went wrong
        </h2>
        <p className="text-muted-foreground text-sm mb-1">
          {error.message || "An unexpected error occurred."}
        </p>
        {error.digest && (
          <p className="text-muted-foreground text-xs mb-4 font-mono">
            Error ID: {error.digest}
          </p>
        )}
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors mt-3"
        >
          <RefreshCw className="w-4 h-4" />
          Try Again
        </button>
      </div>
    </div>
  );
}
