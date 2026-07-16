import { Typography } from "antd";
import { useChat } from "../../application/useChat";
import { useBackend } from "../../application/BackendContext";
import ChatHeader from "../components/ChatHeader";
import MessageList from "../components/MessageList";
import MessageInput from "../components/MessageInput";
import SessionList from "../components/SessionList";

export default function ChatPage() {
  const {
    messages,
    sessions,
    sessionId,
    sending,
    send,
    selectSession,
    createSession,
    removeSession,
  } = useChat();
  const { backend } = useBackend();

  return (
    <div className="chat-page">
      <div className="chat-page__caption">
        <Typography.Text type="secondary">
          Conversando via <b>{backend.label}</b>
        </Typography.Text>
      </div>

      <div className="chat-workspace">
        <aside className="chat-workspace__sessions">
          <SessionList
            sessions={sessions}
            activeSessionId={sessionId}
            onSelect={selectSession}
            onCreate={createSession}
            onDelete={removeSession}
          />
        </aside>

        <div className="chat-shell">
          <div className="chat-phone">
            <ChatHeader />
            <MessageList messages={messages} typing={sending} />
            <MessageInput disabled={sending} onSend={send} />
          </div>
        </div>
      </div>
    </div>
  );
}
