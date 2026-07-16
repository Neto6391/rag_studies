import { App } from "antd";
import { useCallback, useEffect, useState } from "react";
import { ChatMessage, ChatSession } from "../domain/models";
import { toApiError } from "../infrastructure/httpClient";
import {
  deleteSession as deleteSessionApi,
  getHistory,
  listSessions,
  sendMessage,
} from "../services/chatService";
import { useBackend } from "./BackendContext";

function sessionKey(backendId: string): string {
  return `rag.session.${backendId}`;
}

function readActiveSession(backendId: string): string {
  const key = sessionKey(backendId);
  let session = localStorage.getItem(key);
  if (!session) {
    session = crypto.randomUUID();
    localStorage.setItem(key, session);
  }
  return session;
}

function writeActiveSession(backendId: string, sessionId: string): void {
  localStorage.setItem(sessionKey(backendId), sessionId);
}

function sessionFromMessages(
  sessionId: string,
  messages: ChatMessage[]
): ChatSession | null {
  if (messages.length === 0) return null;
  const firstUser = messages.find((m) => m.role === "user");
  return {
    session_id: sessionId,
    message_count: messages.length,
    created_at: messages[0].created_at,
    updated_at: messages[messages.length - 1].created_at,
    preview: firstUser?.content ?? "Nova conversa",
  };
}

export function useChat() {
  const { backend } = useBackend();
  const { notification } = App.useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(() => readActiveSession(backend.id));

  const refreshSessions = useCallback(async () => {
    try {
      const items = await listSessions(backend.baseUrl);
      setSessions(Array.isArray(items) ? items : []);
    } catch (error) {
      const apiError = toApiError(error);
      notification.warning({
        message: "Não foi possível listar as sessões",
        description: apiError.detail,
        placement: "topRight",
        key: `sessions-${backend.id}`,
      });
    }
  }, [backend.baseUrl, backend.id, notification]);

  useEffect(() => {
    setMessages([]);
    const active = readActiveSession(backend.id);
    setSessionId(active);
  }, [backend.id]);

  useEffect(() => {
    let cancelled = false;
    getHistory(backend.baseUrl, sessionId)
      .then((history) => {
        if (!cancelled) setMessages(Array.isArray(history) ? history : []);
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      });
    return () => {
      cancelled = true;
    };
  }, [backend.baseUrl, sessionId]);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions, sessionId, backend.id]);

  useEffect(() => {
    const local = sessionFromMessages(sessionId, messages);
    if (!local) return;
    setSessions((prev) => {
      const exists = prev.some((s) => s.session_id === sessionId);
      if (exists) {
        return prev.map((s) =>
          s.session_id === sessionId
            ? {
                ...s,
                message_count: Math.max(s.message_count, local.message_count),
                updated_at: local.updated_at,
                preview: local.preview || s.preview,
              }
            : s
        );
      }
      return [local, ...prev];
    });
  }, [messages, sessionId]);

  const selectSession = useCallback(
    (id: string) => {
      writeActiveSession(backend.id, id);
      setSessionId(id);
    },
    [backend.id]
  );

  const createSession = useCallback(() => {
    const id = crypto.randomUUID();
    writeActiveSession(backend.id, id);
    setSessionId(id);
    setMessages([]);
  }, [backend.id]);

  const removeSession = useCallback(
    async (id: string) => {
      try {
        await deleteSessionApi(backend.baseUrl, id);
        if (id === sessionId) {
          const next = crypto.randomUUID();
          writeActiveSession(backend.id, next);
          setSessionId(next);
          setMessages([]);
        }
        await refreshSessions();
      } catch (error) {
        const apiError = toApiError(error);
        notification.error({
          message: "Falha ao excluir sessão",
          description: apiError.detail,
          placement: "topRight",
        });
      }
    },
    [backend.baseUrl, backend.id, sessionId, refreshSessions, notification]
  );

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      const optimistic: ChatMessage = {
        id: Date.now(),
        session_id: sessionId,
        role: "user",
        content: trimmed,
        hallucinated: null,
        created_at: new Date().toISOString(),
        sources: null,
      };
      setMessages((prev) => [...prev, optimistic]);
      setSending(true);

      try {
        const res = await sendMessage(backend.baseUrl, sessionId, trimmed);
        const assistant: ChatMessage = {
          id: res.message_id,
          session_id: sessionId,
          role: "assistant",
          content: res.response,
          hallucinated: null,
          created_at: new Date().toISOString(),
          sources: res.results ?? [],
        };
        setMessages((prev) => [...prev, assistant]);
        await refreshSessions();

        window.setTimeout(() => {
          getHistory(backend.baseUrl, sessionId)
            .then((history) => setMessages(history))
            .catch(() => {});
        }, 6000);
      } catch (error) {
        const apiError = toApiError(error);
        notification.error({
          message: "Falha ao enviar mensagem",
          description: apiError.detail,
          placement: "topRight",
        });
        setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
      } finally {
        setSending(false);
      }
    },
    [backend.baseUrl, sessionId, sending, notification, refreshSessions]
  );

  return {
    messages,
    sessions,
    sessionId,
    sending,
    send,
    selectSession,
    createSession,
    removeSession,
  };
}
