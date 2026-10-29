import re

class Preprocessor:
    def __init__(self):
        self.url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')

    def extract_urls(self, text: str) -> list[str]:
        return self.url_pattern.findall(text)

    def clean_text(self, text: str) -> str:
        # Basic cleaning for NLP processing
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

preprocessor = Preprocessor()
