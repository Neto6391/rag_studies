class LLMServiceError(Exception):
    """Falha ao comunicar com o serviço de LLM (auth inválida, timeout, indisponibilidade)."""
