"use client";

import { useEffect, useState } from "react";
import type { BackendHealthResult } from "@/lib/health";

type State =
  | { kind: "loading" }
  | { kind: "connected"; status: string }
  | { kind: "error"; message: string };

export default function BackendStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    async function check() {
      try {
        const res = await fetch("/api/backend-health", {
          cache: "no-store",
          signal: controller.signal,
        });
        const data = (await res.json()) as BackendHealthResult;
        if (data.ok) {
          setState({ kind: "connected", status: data.health.status });
        } else {
          setState({ kind: "error", message: data.error });
        }
      } catch {
        if (!controller.signal.aborted) {
          setState({
            kind: "error",
            message: "Unable to connect to the HelioScan backend.",
          });
        }
      }
    }

    void check();
    return () => controller.abort();
  }, []);

  const label =
    state.kind === "loading"
      ? "Loading"
      : state.kind === "connected"
        ? "Connected"
        : "Connection Error";

  return (
    <section className="border border-gray-400 p-4">
      <h2 className="font-semibold">Backend Status</h2>
      <p className="mt-2" data-testid="backend-status">
        [ {label} ]
      </p>
      {state.kind === "connected" && (
        <div className="mt-4">
          <p className="font-semibold">Health response</p>
          <p>status: {state.status}</p>
        </div>
      )}
      {state.kind === "error" && <p className="mt-4">{state.message}</p>}
    </section>
  );
}
