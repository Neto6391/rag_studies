import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Popconfirm, Typography } from "antd";
import { ChatSession } from "../../domain/models";

function truncate(text: string | null | undefined, max = 42): string {
  const clean = (text ?? "Nova conversa").replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

interface SessionListProps {
  sessions: ChatSession[];
  activeSessionId: string;
  onSelect: (sessionId: string) => void;
  onCreate: () => void;
  onDelete: (sessionId: string) => void;
}

export default function SessionList({
  sessions = [],
  activeSessionId,
  onSelect,
  onCreate,
  onDelete,
}: SessionListProps) {
  return (
    <div className="session-panel">
      <div className="session-panel__header">
        <Typography.Text className="session-panel__title">Sessões</Typography.Text>
        <Button
          type="text"
          size="small"
          icon={<PlusOutlined />}
          onClick={onCreate}
          className="session-panel__new"
          title="Nova conversa"
        />
      </div>

      <div className="session-panel__list">
        {sessions.length === 0 && (
          <div className="session-panel__empty">Nenhuma conversa ainda</div>
        )}
        {sessions.map((session) => {
          const active = session.session_id === activeSessionId;
          return (
            <div
              key={session.session_id}
              className={`session-item ${active ? "session-item--active" : ""}`}
              onClick={() => onSelect(session.session_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(session.session_id);
                }
              }}
            >
              <div className="session-item__body">
                <div className="session-item__preview">{truncate(session.preview)}</div>
                <div className="session-item__meta">
                  {formatDate(session.updated_at)} · {session.message_count} msgs
                </div>
              </div>
              <Popconfirm
                title="Excluir esta sessão?"
                description="As mensagens serão apagadas."
                okText="Excluir"
                cancelText="Cancelar"
                okButtonProps={{ danger: true }}
                onConfirm={(e) => {
                  e?.stopPropagation();
                  onDelete(session.session_id);
                }}
                onCancel={(e) => e?.stopPropagation()}
              >
                <Button
                  type="text"
                  size="small"
                  danger
                  className="session-item__delete"
                  icon={<DeleteOutlined />}
                  onClick={(e) => e.stopPropagation()}
                  title="Excluir sessão"
                />
              </Popconfirm>
            </div>
          );
        })}
      </div>
    </div>
  );
}
