import logging

logger = logging.getLogger(__name__)

class UserRiskEngine:
    def calculate_user_risk(self, avg_message_risk: float, scam_percent: float, behavior_score: float) -> float:
        """
        Calculates the overall risk score for a user.
        """
        # Weighted combination:
        # 50% avg message risk
        # 30% scam percentage
        # 20% behavior score (spamminess/frequency)
        
        score = (avg_message_risk * 0.5) + (scam_percent * 0.3) + (behavior_score * 0.2)
        return min(1.0, score)

user_risk_engine = UserRiskEngine()
