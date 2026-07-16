import { WarningOutlined } from "@ant-design/icons";
import { Avatar } from "antd";
import { ChatMessage } from "../../domain/models";
import { MACHADO_AVATAR } from "./ChatHeader";
import SourceCitations from "./SourceCitations";

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const sources = message.sources ?? [];

  return (
    <div className={`chat-row ${isUser ? "chat-row--user" : "chat-row--bot"}`}>
      {!isUser && (
        <Avatar
          className="chat-avatar"
          size={28}
          src={MACHADO_AVATAR}
          style={{ backgroundColor: "#1f2937", flexShrink: 0 }}
        >
          MA
        </Avatar>
      )}
      <div className="chat-row__content">
        <div className={`chat-bubble ${isUser ? "chat-bubble--user" : "chat-bubble--bot"}`}>
          {message.content}
        </div>
        {!isUser && sources.length > 0 && <SourceCitations sources={sources} />}
        {message.hallucinated === true && (
          <div className="chat-hallucinated">
            <WarningOutlined /> possível invenção factual sobre a obra
          </div>
        )}
      </div>
    </div>
  );
}
