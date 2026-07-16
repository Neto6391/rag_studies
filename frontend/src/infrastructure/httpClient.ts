import axios, { AxiosError, AxiosInstance } from "axios";

export interface ApiError {
  status?: number;
  detail: string;
}

export function toApiError(error: unknown): ApiError {
  const axiosError = error as AxiosError<{ detail?: string }>;
  if (axiosError?.isAxiosError) {
    const detail =
      axiosError.response?.data?.detail ??
      (axiosError.code === "ERR_NETWORK"
        ? "Não foi possível conectar ao backend. Ele está rodando?"
        : axiosError.message);
    return { status: axiosError.response?.status, detail };
  }
  return { detail: "Erro inesperado na aplicação." };
}

export function createHttpClient(baseUrl: string): AxiosInstance {
  return axios.create({
    baseURL: baseUrl,
    timeout: 60000,
    headers: { "Content-Type": "application/json" },
  });
}
