import { createHttpClient } from "../infrastructure/httpClient";
import { DashboardStats } from "../domain/models";

export async function getStats(baseUrl: string): Promise<DashboardStats> {
  const client = createHttpClient(baseUrl);
  const { data } = await client.get<DashboardStats>("/dashboard/");
  return data;
}
