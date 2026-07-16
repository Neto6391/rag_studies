import { Avatar } from "antd";
import { useEffect, useRef } from "react";
import { ChatMessage } from "../../domain/models";
import MessageBubble from "./MessageBubble";
import { MACHADO_AVATAR } from "./ChatHeader";

interface MessageListProps {
  messages: ChatMessage[];
  typing: boolean;
}

export default function MessageList({ messages, typing }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  return (
    <div className="chat-body">
      {messages.length === 0 && !typing && (
        <div className="chat-empty">
          Pergunte algo sobre as obras de Machado de Assis.
          <br />
          Ex.: "Quem é Rubião?", "O que são os olhos de ressaca?"
        </div>
      )}

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {typing && (
        <div className="chat-row chat-row--bot">
          <Avatar
            className="chat-avatar"
            size={28}
            src={MACHADO_AVATAR}
            style={{ backgroundColor: "#1f2937", flexShrink: 0 }}
          >
            MA
          </Avatar>
          <div className="chat-bubble chat-bubble--bot">
            <span className="chat-typing">
              <span />
              <span />
              <span />
            </span>
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}
