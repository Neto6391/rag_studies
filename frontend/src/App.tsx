import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./presentation/layout/AppLayout";
import DashboardPage from "./presentation/pages/DashboardPage";
import ChatPage from "./presentation/pages/ChatPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
