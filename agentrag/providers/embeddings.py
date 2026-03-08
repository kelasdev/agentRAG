from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from time import perf_counter

import httpx

logger = logging.getLogger(__name__)


@contextmanager
def _suppress_stderr() -> None:
    """Temporarily silence C-level stderr noise from llama.cpp."""
    stderr_fd = 2
    saved_stderr_fd = os.dup(stderr_fd)
    try:
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), stderr_fd)
            yield
    finally:
        os.dup2(saved_stderr_fd, stderr_fd)
        os.close(saved_stderr_fd)


class EmbeddingProvider:
    """Embedding provider.

    Supported:
    - llama_cpp_python (CPU-only, n_gpu_layers=0)
    - fastembed
    - openai_compatible
    """

    def __init__(
        self,
        provider: str = "llama_cpp_python",
        model_name: str | None = None,
        model_path: str | None = None,
        n_threads: int = 4,
        openai_base_url: str | None = None,
        openai_api_key: str | None = None,
        request_timeout_seconds: float = 30.0,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.model_path = model_path
        self.openai_base_url = (openai_base_url or "").strip()
        self.openai_api_key = (openai_api_key or "").strip()
        self.request_timeout_seconds = request_timeout_seconds
        self.dimensions = 0
        self._llama = None
        self._fastembed = None
        self._openai_http_client: httpx.Client | None = None

        if self.provider == "llama_cpp_python":
            self._init_llama_cpp(n_threads=n_threads)
        elif self.provider == "fastembed":
            self._init_fastembed()
        elif self.provider == "openai_compatible":
            self._init_openai_compatible()
        else:
            raise ValueError(
                f"Unsupported embedding provider '{self.provider}'. "
                "Supported providers: 'llama_cpp_python', 'fastembed', 'openai_compatible'."
            )

    def _init_llama_cpp(self, n_threads: int) -> None:
        if not self.model_path:
            raise ValueError("LLAMA_CPP_EMBED_MODEL_PATH is required for provider=llama_cpp_python")
        try:
            from llama_cpp import Llama  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "llama_cpp_python is not installed. Install CPU build and retry."
            ) from exc

        started = perf_counter()
        try:
            # Force CPU-only execution.
            self._llama = Llama(
                model_path=self.model_path,
                embedding=True,
                n_threads=n_threads,
                n_gpu_layers=0,
                verbose=False,
            )
            # Read dimensions directly from model metadata to avoid probe embedding call.
            self.dimensions = int(self._llama.n_embd())
        except Exception as exc:
            logger.error(
                "embedding_init_failed provider=llama_cpp_python path=%s n_threads=%s error=%s",
                self.model_path,
                n_threads,
                exc,
            )
            raise RuntimeError(
                f"Failed to initialize llama_cpp embedding model at '{self.model_path}': {exc}"
            ) from exc

        if self.dimensions <= 0:
            raise RuntimeError(
                f"Invalid embedding dimensions ({self.dimensions}) for model '{self.model_path}'"
            )

        logger.info(
            "embedding_init_ok provider=llama_cpp_python path=%s dims=%s n_threads=%s elapsed_ms=%.2f",
            self.model_path,
            self.dimensions,
            n_threads,
            (perf_counter() - started) * 1000,
        )

    def _init_fastembed(self) -> None:
        if not self.model_name:
            raise ValueError("EMBEDDING_MODEL is required for provider=fastembed")
        try:
            from fastembed import TextEmbedding  # type: ignore
        except Exception as exc:
            raise RuntimeError("fastembed is not installed. Install it and retry.") from exc

        started = perf_counter()
        try:
            self._fastembed = TextEmbedding(model_name=self.model_name)
            probe = list(self._fastembed.embed(["dimension probe"]))
            if not probe:
                raise RuntimeError("fastembed returned empty embedding response")
            self.dimensions = int(len(probe[0]))
        except Exception as exc:
            logger.error(
                "embedding_init_failed provider=fastembed model=%s error=%s",
                self.model_name,
                exc,
            )
            raise RuntimeError(
                f"Failed to initialize fastembed model '{self.model_name}': {exc}"
            ) from exc

        if self.dimensions <= 0:
            raise RuntimeError(
                f"Invalid embedding dimensions ({self.dimensions}) for model '{self.model_name}'"
            )

        logger.info(
            "embedding_init_ok provider=fastembed model=%s dims=%s elapsed_ms=%.2f",
            self.model_name,
            self.dimensions,
            (perf_counter() - started) * 1000,
        )

    def _init_openai_compatible(self) -> None:
        if not self.model_name:
            raise ValueError("EMBEDDING_MODEL is required for provider=openai_compatible")
        if not self.openai_base_url:
            raise ValueError(
                "OPENAI_COMPATIBLE_BASE_URL is required for provider=openai_compatible"
            )
        started = perf_counter()
        self._openai_http_client = httpx.Client(timeout=self.request_timeout_seconds)
        try:
            probe = self._openai_embed_batch(["dimension probe"])
            if not probe:
                raise RuntimeError("openai-compatible endpoint returned empty embedding response")
            self.dimensions = int(len(probe[0]))
        except Exception as exc:
            logger.error(
                "embedding_init_failed provider=openai_compatible base_url=%s model=%s error=%s",
                self.openai_base_url,
                self.model_name,
                exc,
            )
            raise RuntimeError(
                "Failed to initialize openai-compatible embedding model "
                f"'{self.model_name}' at '{self.openai_base_url}': {exc}"
            ) from exc

        if self.dimensions <= 0:
            raise RuntimeError(
                f"Invalid embedding dimensions ({self.dimensions}) for model '{self.model_name}'"
            )

        logger.info(
            "embedding_init_ok provider=openai_compatible base_url=%s model=%s dims=%s elapsed_ms=%.2f",
            self.openai_base_url,
            self.model_name,
            self.dimensions,
            (perf_counter() - started) * 1000,
        )

    def _openai_embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._openai_http_client is None:
            raise RuntimeError("openai_compatible HTTP client is not initialized")
        url = f"{self.openai_base_url.rstrip('/')}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"

        try:
            response = self._openai_http_client.post(
                url,
                headers=headers,
                json={"model": self.model_name, "input": texts},
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            vectors = [list(item["embedding"]) for item in data]
        except Exception as exc:
            raise RuntimeError(f"openai-compatible embedding request failed: {exc}") from exc

        if len(vectors) != len(texts):
            raise RuntimeError(
                f"openai-compatible returned {len(vectors)} embeddings for {len(texts)} inputs"
            )
        return vectors

    def embed(self, text: str) -> list[float]:
        started = perf_counter()
        if self.provider == "llama_cpp_python":
            if self._llama is None:
                raise RuntimeError("llama_cpp provider is not initialized")
            with _suppress_stderr():
                out = self._llama.create_embedding(text)
            vec = list(out["data"][0]["embedding"])
        elif self.provider == "fastembed":
            if self._fastembed is None:
                raise RuntimeError("fastembed provider is not initialized")
            out = list(self._fastembed.embed([text]))
            if not out:
                raise RuntimeError("fastembed returned empty embedding result")
            vec = list(out[0])
        elif self.provider == "openai_compatible":
            vec = self._openai_embed_batch([text])[0]
        else:
            raise RuntimeError(f"Unsupported provider at runtime: {self.provider}")
        logger.debug(
            "embedding_call_ok provider=%s chars=%s dims=%s elapsed_ms=%.2f",
            self.provider,
            len(text),
            len(vec),
            (perf_counter() - started) * 1000,
        )
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        
        if self.provider == "fastembed":
            if self._fastembed is None:
                raise RuntimeError("fastembed provider is not initialized")
            started = perf_counter()
            vectors = [list(vec) for vec in self._fastembed.embed(texts)]
            logger.debug(
                "embedding_batch_ok provider=fastembed count=%s dims=%s elapsed_ms=%.2f",
                len(texts),
                self.dimensions,
                (perf_counter() - started) * 1000,
            )
            return vectors
        if self.provider == "openai_compatible":
            started = perf_counter()
            vectors = self._openai_embed_batch(texts)
            logger.debug(
                "embedding_batch_ok provider=openai_compatible count=%s dims=%s elapsed_ms=%.2f",
                len(texts),
                self.dimensions,
                (perf_counter() - started) * 1000,
            )
            return vectors
        if self.provider == "llama_cpp_python":
            if self._llama is None:
                raise RuntimeError("llama_cpp provider is not initialized")
            started = perf_counter()
            vectors = []
            with _suppress_stderr():
                # Use batch processing for llama.cpp with memory optimization
                for text in texts:
                    out = self._llama.create_embedding(text)
                    vectors.append(list(out["data"][0]["embedding"]))
            logger.debug(
                "embedding_batch_ok provider=llama_cpp_python count=%s dims=%s elapsed_ms=%.2f",
                len(texts),
                self.dimensions,
                (perf_counter() - started) * 1000,
            )
            return vectors
        return [self.embed(t) for t in texts]
