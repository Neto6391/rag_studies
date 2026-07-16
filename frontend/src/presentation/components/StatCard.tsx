import { Card, Statistic } from "antd";
import { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  color: string;
  suffix?: ReactNode;
}

export default function StatCard({ title, value, icon, color, suffix }: StatCardProps) {
  return (
    <Card variant="borderless" style={{ borderRadius: 14, height: "100%" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Statistic
          title={title}
          value={value}
          suffix={suffix}
          valueStyle={{ fontWeight: 700, fontSize: 26 }}
        />
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 12,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: `${color}1a`,
            color,
            fontSize: 22,
          }}
        >
          {icon}
        </div>
      </div>
    </Card>
  );
}
