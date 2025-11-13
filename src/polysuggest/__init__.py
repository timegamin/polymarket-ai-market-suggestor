from importlib.metadata import version

__all__ = ["get_version"]


def get_version() -> str:
  try:
    return version("polymarket-ai-market-suggestor")
  except Exception:
    return "0.1.0"

