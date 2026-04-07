"""
조건 계산기 추상 베이스 클래스
"""
from abc import ABC, abstractmethod


class BaseCondition(ABC):
    """
    모든 조건 계산기의 기반 클래스.
    score()는 0~100 사이 점수를 반환.
    """
    name: str = "unnamed"

    @abstractmethod
    def score(self, code: str, data: dict) -> tuple[float, str]:
        """
        조건 점수 계산
        Args:
            code: 종목코드
            data: {
                "daily"  : [{"date","open","high","low","close","volume"}, ...] 최신순
                "min60"  : [{"time","open","high","low","close","volume"}, ...]
                "min15"  : [...]
                "supply" : [{"date","foreign_net","inst_net","total_net"}, ...]
                "price"  : t1102 현재가 dict
            }
        Returns:
            (score: float 0~100, detail: str)
        """
        pass

    def check_screening(self, code: str, data: dict) -> bool:
        """
        스크리닝 조건 통과 여부 (True/False)
        기본 구현: score >= 50 이면 통과
        스크리닝 조건 클래스에서 오버라이드 가능
        """
        s, _ = self.score(code, data)
        return s >= 50
