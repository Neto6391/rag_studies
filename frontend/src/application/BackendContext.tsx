import {
  createContext,
  useContext,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { BackendId, BackendOption } from "../domain/models";

const AGENTIC_URL = import.meta.env.VITE_AGENTIC_URL ?? "http://localhost:8000";
const SIMPLE_URL = import.meta.env.VITE_SIMPLE_URL ?? "http://localhost:8001";
const MANGABA_URL = import.meta.env.VITE_MANGABA_URL ?? "http://localhost:8002";

export const BACKENDS: Record<BackendId, BackendOption> = {
  agentic: { id: "agentic", label: "Agentic RAG", baseUrl: AGENTIC_URL },
  simple: { id: "simple", label: "Simple RAG", baseUrl: SIMPLE_URL },
  mangaba: { id: "mangaba", label: "Mangaba RAG", baseUrl: MANGABA_URL },
};

const STORAGE_KEY = "rag.backend";

interface BackendContextValue {
  backend: BackendOption;
  setBackend: (id: BackendId) => void;
}

const BackendContext = createContext<BackendContextValue | undefined>(undefined);

export function BackendProvider({ children }: { children: ReactNode }) {
  const [id, setId] = useState<BackendId>(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as BackendId | null;
    return stored && stored in BACKENDS ? stored : "agentic";
  });

  const value = useMemo<BackendContextValue>(
    () => ({
      backend: BACKENDS[id],
      setBackend: (next) => {
        localStorage.setItem(STORAGE_KEY, next);
        setId(next);
      },
    }),
    [id]
  );

  return (
    <BackendContext.Provider value={value}>{children}</BackendContext.Provider>
  );
}

export function useBackend(): BackendContextValue {
  const ctx = useContext(BackendContext);
  if (!ctx) throw new Error("useBackend deve ser usado dentro de BackendProvider");
  return ctx;
}
