import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TextClassifier:
    """Zero-shot text classification for message categorization.
    
    Uses XLM-RoBERTa trained on multilingual NLI data to classify
    messages into: scam, phishing, spam, normal.
    
    Supports 100+ languages including EN, RU, UZ natively.
    Model is loaded lazily on first call.
    """

    # "normal communication" gives better semantic separation than bare "normal"
    # in zero-shot NLI. Normalized back to "normal" in output for compatibility.
    CANDIDATE_LABELS = ["scam", "phishing", "spam", "normal communication"]

    def __init__(self):
        self._classifier = None

    def _load_model(self):
        if self._classifier is None:
            try:
                from transformers import pipeline
                model_path = Path(__file__).resolve().parents[1] / "ai"
                model_file = model_path / "pytorch_model.bin"
                model_target = str(model_path) if model_file.exists() else "vicgalle/xlm-roberta-large-xnli-anli"
                logger.info(f"Loading classifier from {model_target}...")
                self._classifier = pipeline(
                    "zero-shot-classification",
                    model=model_target,
                    device=-1,  # CPU
                )
                logger.info("Classification model loaded successfully.")
            except ImportError:
                logger.error(
                    "transformers not installed. "
                    "Run: pip install transformers torch"
                )
            except Exception as e:
                logger.error(f"Failed to load classification model: {e}")

    def classify(self, text: str) -> dict:
        """Classify a message into one of the candidate labels.
        
        Supports English, Russian, Uzbek, and 100+ other languages.
        
        Args:
            text: The message text to classify.
            
        Returns:
            Dict with keys:
                - label: str (best matching label, normalized)
                - score: float (confidence 0–1)
                - all_scores: dict (all labels with their scores)
        """
        default = {
            "label": "normal",
            "score": 0.0,
            "all_scores": {label: 0.0 for label in self.CANDIDATE_LABELS},
        }

        if not text or not text.strip():
            return default

        self._load_model()
        if self._classifier is None:
            return default

        try:
            # Truncate very long texts to avoid excessive processing
            truncated = text[:512]
            result = self._classifier(
                truncated,
                candidate_labels=self.CANDIDATE_LABELS,
                multi_label=False,
            )

            best_label = result["labels"][0]
            best_score = result["scores"][0]
            all_scores = dict(zip(result["labels"], result["scores"]))

            # Normalize "normal communication" → "normal" for downstream compat
            normalized_label = "normal" if best_label == "normal communication" else best_label

            return {
                "label": normalized_label,
                "score": round(best_score, 4),
                "all_scores": {
                    label: round(score, 4) 
                    for label, score in all_scores.items()
                },
            }
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return default


classifier = TextClassifier()
