import { SendOutlined } from "@ant-design/icons";
import { Button, Input } from "antd";
import { useState } from "react";

interface MessageInputProps {
  disabled: boolean;
  onSend: (text: string) => void;
}

export default function MessageInput({ disabled, onSend }: MessageInputProps) {
  const [value, setValue] = useState("");

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  };

  return (
    <div className="chat-footer">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onPressEnter={submit}
        placeholder="Escreva uma mensagem..."
        style={{ borderRadius: 20 }}
        disabled={disabled}
      />
      <Button
        type="primary"
        shape="circle"
        icon={<SendOutlined />}
        onClick={submit}
        loading={disabled}
      />
    </div>
  );
}
