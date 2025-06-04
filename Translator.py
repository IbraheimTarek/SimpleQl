
from __future__ import annotations
import functools
from typing import Dict, Optional
from langdetect import detect  # simple, fast lang detection
from transformers import pipeline, Pipeline


class Translator:
    """Detect the input language and translate it to English if needed."""

    #: Map ISO‑639 language codes to dedicated HF translation checkpoints
    _LANG2CKPT: Dict[str, str] = {
        "ar": "Helsinki-NLP/opus-mt-ar-en",
        # "es": "Helsinki-NLP/opus-mt-es-en",
        # "de": "Helsinki-NLP/opus-mt-de-en",
    }

    _FALLBACK_CKPT = "facebook/nllb-200-distilled-600M"

    def __init__(self, device: Optional[int] = None):
        """Initialise without loading any heavy models up front.

        Parameters
        ----------
        device : int | None
            GPU id (0, 1, …) on which to load the models. Leave ``None`` for CPU.
        """
        self.device = device
        # Lazy‑load pipelines on first use to keep startup fast.
        self._pipelines: Dict[str, Pipeline] = {}


    def detect_language(self, text: str) -> str:
        """Return ISO-639-1 language code (e.g. 'ar', 'es', 'de', 'en')."""
        # langdetect may raise LangDetectException on empty / too‑short strings
        try:
            return detect(text)
        except Exception:
            return "unknown"

    def translate(self, text: str) -> str:
        """Translate *text* to English; if already English, return unchanged."""
        lang = self.detect_language(text)
        if lang in ("en", "unknown"):
            return text

        pipe = self._get_pipeline(lang)
        out = pipe(text, max_length=512)
        # HF translation pipeline returns list[dict]; take first 'translation_text'
        return out[0]["translation_text"]

    def _get_pipeline(self, lang: str) -> Pipeline:
        """Fetch (or build and cache) the correct translation pipeline."""
        if lang not in self._pipelines:
            ckpt = self._LANG2CKPT.get(lang, self._FALLBACK_CKPT)
            self._pipelines[lang] = pipeline(
                "translation", model=ckpt, device=self.device
            )
        return self._pipelines[lang]


#  quick self‑test 
if __name__ == "__main__":
    tr = Translator()
    for sample in [
        "ما هي عاصمة إسبانيا؟",
        # "¿Cuál es la capital de España?",
        # "Wie spät ist es?",
    ]:
        print("<-", sample)
        print("->", tr.translate(sample))
