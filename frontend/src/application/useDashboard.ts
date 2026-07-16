import { App } from "antd";
import { useCallback, useEffect, useState } from "react";
import { DashboardStats } from "../domain/models";
import { toApiError } from "../infrastructure/httpClient";
import { getStats } from "../services/dashboardService";
import { useBackend } from "./BackendContext";

export function useDashboard() {
  const { backend } = useBackend();
  const { notification } = App.useApp();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getStats(backend.baseUrl);
      setStats(data);
    } catch (error) {
      const apiError = toApiError(error);
      notification.error({
        message: "Falha ao carregar o dashboard",
        description: apiError.detail,
        placement: "topRight",
      });
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, [backend.baseUrl, notification]);

  useEffect(() => {
    load();
  }, [load]);

  return { stats, loading, reload: load };
}
