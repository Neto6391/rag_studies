import { createHttpClient } from "../infrastructure/httpClient";
import { ChatMessage, ChatResponse, ChatSession } from "../domain/models";

export async function sendMessage(
  baseUrl: string,
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const client = createHttpClient(baseUrl);
  const { data } = await client.post<ChatResponse>("/chat/", {
    session_id: sessionId,
    message,
  });
  return data;
}

export async function getHistory(
  baseUrl: string,
  sessionId: string
): Promise<ChatMessage[]> {
  const client = createHttpClient(baseUrl);
  const { data } = await client.get<{ messages?: ChatMessage[] }>(
    `/chat/${sessionId}`
  );
  return Array.isArray(data.messages) ? data.messages : [];
}

export async function listSessions(baseUrl: string): Promise<ChatSession[]> {
  const client = createHttpClient(baseUrl);
  try {
    const { data } = await client.get<{ sessions?: ChatSession[] }>("/sessions");
    if (Array.isArray(data.sessions)) return data.sessions;
  } catch {
  }
  const { data } = await client.get<{ sessions?: ChatSession[] }>("/chat/sessions");
  return Array.isArray(data.sessions) ? data.sessions : [];
}

export async function deleteSession(
  baseUrl: string,
  sessionId: string
): Promise<void> {
  const client = createHttpClient(baseUrl);
  try {
    await client.delete(`/sessions/${sessionId}`);
  } catch {
    await client.delete(`/chat/${sessionId}`);
  }
}
