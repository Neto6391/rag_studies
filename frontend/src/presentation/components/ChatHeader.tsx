import { Avatar } from "antd";

export const MACHADO_AVATAR =
  "https://upload.wikimedia.org/wikipedia/commons/2/24/Machado_de_Assis_1904.jpg";

export default function ChatHeader() {
  return (
    <div className="chat-header">
      <Avatar size={44} src={MACHADO_AVATAR} style={{ backgroundColor: "#1f2937" }}>
        MA
      </Avatar>
      <div className="chat-header__meta">
        <span className="chat-header__name">Machado de Assis</span>
        <span className="chat-header__status">
          <span className="chat-header__dot" />
          online · responde pelo corpus
        </span>
      </div>
    </div>
  );
}
