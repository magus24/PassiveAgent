import re

class PatternDetector:
    def __init__(self):
        # Known scam/spam patterns in Uzbek and Russian
        self.patterns = [
            re.compile(r'\bqo[\'‘]shib beramiz\b', re.IGNORECASE),
            re.compile(r'\baksiya\b', re.IGNORECASE),
            re.compile(r'\barzon\b', re.IGNORECASE),
            re.compile(r'\btez pul\b', re.IGNORECASE),
            re.compile(r'\b1000\s?ta odam\b', re.IGNORECASE),
            re.compile(r'\bUSDT\b', re.IGNORECASE),
            re.compile(r'\bкрипта\b', re.IGNORECASE),
            re.compile(r'\bгарантированный\b', re.IGNORECASE),
            re.compile(r'\bвыигрыш\b', re.IGNORECASE),
            re.compile(r'\bлохотрон\b', re.IGNORECASE)
        ]
        
    def detect_patterns(self, text: str) -> list[str]:
        if not text:
            return []
            
        matches = []
        for pattern in self.patterns:
            found = pattern.findall(text)
            if found:
                matches.extend(found)
                
        # Return unique normalized matches
        return list(set([m.lower() for m in matches]))

pattern_detector = PatternDetector()
