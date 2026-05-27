from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from scipy import stats
import logging

from src.contracts import ValidationResult, HypothesisTestData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StatisticalValidator:
    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    def validate_hypothesis(self, data: HypothesisTestData) -> ValidationResult:
        test_type = data.test_type.lower()
        
        if test_type == "t_test":
            return self._perform_t_test(data)
        elif test_type == "mann_whitney":
            return self._perform_mann_whitney(data)
        elif test_type == "ks_test":
            return self._perform_ks_test(data)
        else:
            logger.warning(f"Unknown test type: {test_type}, using t-test")
            return self._perform_t_test(data)

    def _perform_t_test(self, data: HypothesisTestData) -> ValidationResult:
        try:
            group_a = np.array(data.group_a)
            group_b = np.array(data.group_b)
            
            t_stat, p_value = stats.ttest_ind(group_a, group_b)
            
            effect_size = self._compute_cohens_d(group_a, group_b)
            
            hypothesis_supported = p_value < self.alpha
            confidence_level = 1.0 - p_value
            
            conclusion = self._generate_conclusion(
                hypothesis_supported,
                p_value,
                effect_size,
                "independent t-test"
            )
            
            return ValidationResult(
                hypothesis_supported=hypothesis_supported,
                p_value=p_value,
                confidence_level=confidence_level,
                effect_size=effect_size,
                conclusion=conclusion
            )

        except Exception as e:
            logger.error(f"T-test failed: {e}")
            return self._generate_error_result(str(e))

    def _perform_mann_whitney(self, data: HypothesisTestData) -> ValidationResult:
        try:
            group_a = np.array(data.group_a)
            group_b = np.array(data.group_b)
            
            u_stat, p_value = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
            
            effect_size = self._compute_rank_biserial_correlation(u_stat, len(group_a), len(group_b))
            
            hypothesis_supported = p_value < self.alpha
            confidence_level = 1.0 - p_value
            
            conclusion = self._generate_conclusion(
                hypothesis_supported,
                p_value,
                effect_size,
                "Mann-Whitney U test"
            )
            
            return ValidationResult(
                hypothesis_supported=hypothesis_supported,
                p_value=p_value,
                confidence_level=confidence_level,
                effect_size=effect_size,
                conclusion=conclusion
            )

        except Exception as e:
            logger.error(f"Mann-Whitney test failed: {e}")
            return self._generate_error_result(str(e))

    def _perform_ks_test(self, data: HypothesisTestData) -> ValidationResult:
        try:
            group_a = np.array(data.group_a)
            group_b = np.array(data.group_b)
            
            ks_stat, p_value = stats.ks_2samp(group_a, group_b)
            
            effect_size = ks_stat
            
            hypothesis_supported = p_value < self.alpha
            confidence_level = 1.0 - p_value
            
            conclusion = self._generate_conclusion(
                hypothesis_supported,
                p_value,
                effect_size,
                "Kolmogorov-Smirnov test"
            )
            
            return ValidationResult(
                hypothesis_supported=hypothesis_supported,
                p_value=p_value,
                confidence_level=confidence_level,
                effect_size=effect_size,
                conclusion=conclusion
            )

        except Exception as e:
            logger.error(f"KS test failed: {e}")
            return self._generate_error_result(str(e))

    def _compute_cohens_d(self, group_a: np.ndarray, group_b: np.ndarray) -> float:
        n1, n2 = len(group_a), len(group_b)
        var1, var2 = np.var(group_a, ddof=1), np.var(group_b, ddof=1)
        
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        cohens_d = (np.mean(group_a) - np.mean(group_b)) / pooled_std
        return cohens_d

    def _compute_rank_biserial_correlation(self, u_stat: float, n1: int, n2: int) -> float:
        return 1 - (2 * u_stat) / (n1 * n2)

    def _generate_conclusion(self, supported: bool, p_value: float, 
                            effect_size: float, test_name: str) -> str:
        effect_interpretation = self._interpret_effect_size(effect_size)
        
        if supported:
            return (f"Hypothesis supported by {test_name} "
                   f"(p={p_value:.4f}, {effect_interpretation}). "
                   f"Statistically significant difference detected.")
        else:
            return (f"Hypothesis not supported by {test_name} "
                   f"(p={p_value:.4f}, {effect_interpretation}). "
                   f"No statistically significant difference detected.")

    def _interpret_effect_size(self, effect_size: float) -> str:
        abs_effect = abs(effect_size)
        
        if abs_effect < 0.2:
            return f"effect_size={effect_size:.3f} (negligible)"
        elif abs_effect < 0.5:
            return f"effect_size={effect_size:.3f} (small)"
        elif abs_effect < 0.8:
            return f"effect_size={effect_size:.3f} (medium)"
        else:
            return f"effect_size={effect_size:.3f} (large)"

    def _generate_error_result(self, error_msg: str) -> ValidationResult:
        return ValidationResult(
            hypothesis_supported=False,
            p_value=1.0,
            confidence_level=0.0,
            effect_size=0.0,
            conclusion=f"Validation failed: {error_msg}"
        )

    def compute_significance(self, group_a: List[float], group_b: List[float], 
                           test_type: str = "t_test") -> Tuple[float, float]:
        try:
            group_a = np.array(group_a)
            group_b = np.array(group_b)
            
            if test_type == "t_test":
                _, p_value = stats.ttest_ind(group_a, group_b)
            elif test_type == "mann_whitney":
                _, p_value = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
            elif test_type == "ks_test":
                _, p_value = stats.ks_2samp(group_a, group_b)
            else:
                _, p_value = stats.ttest_ind(group_a, group_b)
            
            confidence_level = 1.0 - p_value
            return p_value, confidence_level

        except Exception as e:
            logger.error(f"Significance computation failed: {e}")
            return 1.0, 0.0

    def compare_to_baseline(self, experimental: List[float], 
                           baseline: List[float]) -> Dict[str, Any]:
        try:
            experimental = np.array(experimental)
            baseline = np.array(baseline)
            
            p_value, confidence_level = self.compute_significance(
                experimental.tolist(), baseline.tolist()
            )
            
            effect_size = self._compute_cohens_d(experimental, baseline)
            
            return {
                "p_value": p_value,
                "confidence_level": confidence_level,
                "effect_size": effect_size,
                "experimental_mean": np.mean(experimental),
                "baseline_mean": np.mean(baseline),
                "difference": np.mean(experimental) - np.mean(baseline),
                "significant": p_value < self.alpha
            }

        except Exception as e:
            logger.error(f"Baseline comparison failed: {e}")
            return {
                "p_value": 1.0,
                "confidence_level": 0.0,
                "effect_size": 0.0,
                "significant": False,
                "error": str(e)
            }

    def compute_gini(self, values: List[float]) -> float:
        try:
            values = np.array(values)
            sorted_values = np.sort(values)
            n = len(values)
            
            if n == 0 or np.sum(values) == 0:
                return 0.0
            
            cumulative = np.cumsum(sorted_values, dtype=float)
            cumulative = cumulative / cumulative[-1]
            gini = (n + 1 - 2 * np.sum(cumulative)) / n
            
            return max(0.0, min(1.0, gini))

        except Exception as e:
            logger.error(f"Gini computation failed: {e}")
            return 0.0

    def compute_mean_hostility(self, beliefs: List[Dict[str, float]]) -> float:
        try:
            if not beliefs:
                return 0.0
            
            hostility_values = [b.get("hostility", 0.0) for b in beliefs]
            return np.mean(hostility_values)

        except Exception as e:
            logger.error(f"Mean hostility computation failed: {e}")
            return 0.0

    def compute_confidence_interval(self, values: List[float], 
                                   confidence: float = 0.95) -> Tuple[float, float]:
        try:
            values = np.array(values)
            n = len(values)
            
            if n < 2:
                return (np.mean(values), np.mean(values))
            
            mean = np.mean(values)
            std_err = stats.sem(values)
            
            h = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
            
            return (mean - h, mean + h)

        except Exception as e:
            logger.error(f"Confidence interval computation failed: {e}")
            return (0.0, 0.0)
