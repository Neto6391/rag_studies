import {
  AlertOutlined,
  DatabaseOutlined,
  MessageOutlined,
  ReadOutlined,
} from "@ant-design/icons";
import { Pie } from "@ant-design/plots";
import { Card, Col, Empty, Row, Skeleton, Space, Tag, Typography } from "antd";
import { useDashboard } from "../../application/useDashboard";
import { useBackend } from "../../application/BackendContext";
import StatCard from "../components/StatCard";

export default function DashboardPage() {
  const { stats, loading } = useDashboard();
  const { backend } = useBackend();

  const total = stats?.corpus_breakdown?.reduce((acc, item) => acc + item.count, 0) ?? 0;
  const predominant = stats?.corpus_breakdown?.[0];
  const predominantPct =
    predominant && total ? Math.round((predominant.count / total) * 100) : 0;

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <Typography.Title level={3} style={{ marginBottom: 4 }}>
          Dashboard
        </Typography.Title>
        <Typography.Text type="secondary">
          Métricas do corpus e das conversas · fonte:{" "}
          <Tag color="geekblue">{backend.label}</Tag>
        </Typography.Text>
      </div>

      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : !stats ? (
        <Empty description="Sem dados — o backend está rodando?" />
      ) : (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} xl={6}>
              <StatCard
                title="Registros no corpus"
                value={stats.corpus_total}
                icon={<DatabaseOutlined />}
                color="#4f46e5"
              />
            </Col>
            <Col xs={24} sm={12} xl={6}>
              <StatCard
                title="Corpus predominante"
                value={stats.predominant_corpus}
                suffix={<span style={{ fontSize: 14 }}>· {predominantPct}%</span>}
                icon={<ReadOutlined />}
                color="#0ea5e9"
              />
            </Col>
            <Col xs={24} sm={12} xl={6}>
              <StatCard
                title="Alucinações detectadas"
                value={stats.hallucination_count}
                icon={<AlertOutlined />}
                color="#f59e0b"
              />
            </Col>
            <Col xs={24} sm={12} xl={6}>
              <StatCard
                title="Mensagens · Sessões"
                value={`${stats.total_messages} · ${stats.total_sessions}`}
                icon={<MessageOutlined />}
                color="#10b981"
              />
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="Composição do corpus por obra" style={{ borderRadius: 14 }}>
                <Pie
                  data={stats.corpus_breakdown}
                  angleField="count"
                  colorField="name"
                  radius={0.9}
                  innerRadius={0.5}
                  height={280}
                  legend={{ color: { position: "bottom" } }}
                  label={{ text: "count" }}
                />
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="Detalhamento" style={{ borderRadius: 14 }}>
                <Space direction="vertical" style={{ width: "100%" }} size="middle">
                  {stats.corpus_breakdown.map((item) => (
                    <div
                      key={item.name}
                      style={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography.Text>{item.name}</Typography.Text>
                      <Typography.Text strong>
                        {item.count}{" "}
                        <Typography.Text type="secondary">
                          ({total ? Math.round((item.count / total) * 100) : 0}%)
                        </Typography.Text>
                      </Typography.Text>
                    </div>
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </Space>
  );
}
