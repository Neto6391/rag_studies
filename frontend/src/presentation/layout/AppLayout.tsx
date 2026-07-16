import {
  BellOutlined,
  DashboardOutlined,
  MessageOutlined,
} from "@ant-design/icons";
import { Avatar, Dropdown, Layout, Menu, Segmented, Space, Typography } from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useBackend } from "../../application/BackendContext";
import { BackendId } from "../../domain/models";

const { Sider, Header, Content } = Layout;

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { backend, setBackend } = useBackend();

  const selectedKey = location.pathname === "/chat" ? "/chat" : "/";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth="0" style={{ background: "#0f172a" }}>
        <div className="brand">
          <span className="brand__badge">✦</span>
          <span>RAG Studies</span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          style={{ background: "transparent" }}
          onClick={(e) => navigate(e.key)}
          items={[
            { key: "/", icon: <DashboardOutlined />, label: "Dashboard" },
            { key: "/chat", icon: <MessageOutlined />, label: "Chat" },
          ]}
        />
      </Sider>

      <Layout>
        <Header
          style={{
            background: "#fff",
            padding: "0 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <Segmented
            value={backend.id}
            onChange={(value) => setBackend(value as BackendId)}
            options={[
              { label: "Agentic RAG", value: "agentic" },
              { label: "Simple RAG", value: "simple" },
              { label: "Mangaba RAG", value: "mangaba" },
            ]}
          />

          <Space size="large">
            <BellOutlined style={{ fontSize: 18, color: "#64748b" }} />
            <Dropdown
              menu={{
                items: [
                  { key: "profile", label: "Meu perfil" },
                  { key: "logout", label: "Sair" },
                ],
              }}
            >
              <Space style={{ cursor: "pointer" }}>
                <Avatar style={{ backgroundColor: "#4f46e5" }}>JN</Avatar>
                <Typography.Text strong>José Neto</Typography.Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
