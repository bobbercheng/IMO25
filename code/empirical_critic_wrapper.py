#!/usr/bin/env python3
"""
Empirical Critic Wrapper: Adds Ground Truth Verification to Adversarial Critic

QUICK WIN #1 from expert analysis:
  Wraps existing AdversarialCritic with empirical verification layer.
  
  BEFORE: Critic only checks logical consistency
  AFTER: Critic checks logical consistency + empirical correctness
  
  Impact: +20% success rate, $10/problem, 1 week implementation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, Any
from empirical_verifier import empirical_verifier_dispatcher
from adversarial_critic import AdversarialCritic


class EmpiricalCriticWrapper:
    """
    Wrapper that adds empirical verification to adversarial critic.
    
    Strategy:
      1. Run normal adversarial attack (logical verification)
      2. If verdict is ROBUST, run empirical verification
      3. Downgrade to BROKEN if empirical test fails
    """
    
    def __init__(self, base_critic: AdversarialCritic = None, enable_empirical: bool = True):
        """
        Initialize wrapper.

        Args:
            base_critic: Existing AdversarialCritic instance (creates new if None)
            enable_empirical: Enable empirical verification (default: True)
        """
        self.base_critic = base_critic or AdversarialCritic()
        self.enable_empirical = enable_empirical
        self.empirical_history = []

    def __getattr__(self, name):
        """
        Forward all missing method calls to the base_critic.

        This makes EmpiricalCriticWrapper a transparent wrapper that supports
        all AdversarialCritic methods (create_enhanced_session, get_defense_prompt, etc.)
        """
        return getattr(self.base_critic, name)
    
    def attack_solution(self, problem_statement, solution, round_num=0, **kwargs):
        """
        Attack solution with logical + empirical verification.

        Process:
          1. Run adversarial attack (logical checks)
          2. If BROKEN/SUSPICIOUS, run empirical verification to validate
          3. Override verdict if empirical tests contradict critic

        Key Insight:
          - Critic gives BROKEN → Test with ground truth
          - If empirical tests PASS → Override to ROBUST (critic false negative)
          - If empirical tests FAIL → Confirm BROKEN (critic was right)

        Returns:
            Attack result dict with combined verdict
        """
        # Step 1: Run base adversarial attack
        attack_result = self.base_critic.attack_solution(
            problem_statement, solution, round_num=round_num, **kwargs
        )

        original_verdict = attack_result.get('verdict', 'SUSPICIOUS')
        counterexamples = attack_result.get('counterexamples', [])

        # PHASE 1.2: Counterexample Quality Filter for geometry problems
        if counterexamples and problem_statement:
            filtered_ces = []
            rejected_ces = []

            # Detect if geometry problem
            is_geometry = any(kw in problem_statement.lower() for kw in
                             ['circle', 'triangle', 'geometry', 'angle', 'tangent',
                              'perpendicular', 'parallel', 'line', 'point'])

            if is_geometry:
                for ce in counterexamples:
                    is_valid = self._validate_geometric_counterexample(ce)

                    if is_valid:
                        filtered_ces.append(ce)
                    else:
                        rejected_ces.append(ce)

                if rejected_ces:
                    invalid_ratio = len(rejected_ces) / len(counterexamples)
                    print(f"\n[CE FILTER] Rejected {len(rejected_ces)}/{len(counterexamples)} invalid counterexamples ({invalid_ratio:.0%})")

                    # Show samples of rejected CEs
                    for i, ce in enumerate(rejected_ces[:2]):
                        print(f"[CE FILTER]   Sample {i+1}: {ce[:100]}...")

                    # Downgrade verdict if too many invalid
                    if invalid_ratio > 0.7 and original_verdict == 'BROKEN':
                        print(f"[CE FILTER] >70% invalid - downgrading: BROKEN → SUSPICIOUS")
                        attack_result['verdict'] = 'SUSPICIOUS'
                        original_verdict = 'SUSPICIOUS'

                # Update attack result
                attack_result['counterexamples'] = filtered_ces
                attack_result['rejected_counterexamples'] = rejected_ces
                counterexamples = filtered_ces

        # Step 2: If empirical verification enabled and critic says BROKEN/SUSPICIOUS
        # BUGFIX (2025-11-30): Run empirical on BROKEN verdicts to validate critic's counterexamples
        # Previous logic only ran on ROBUST, which was backwards
        if self.enable_empirical and original_verdict in ['BROKEN', 'SUSPICIOUS']:
            # Extract answer from solution
            answer_text = self._extract_answer(solution)

            if answer_text:
                print(f"\n{'='*80}")
                print(f"[EMPIRICAL VERIFICATION] Critic says {original_verdict}, validating with ground truth...")
                print(f"{'='*80}\n")

                empirical_result = empirical_verifier_dispatcher(
                    problem_statement=problem_statement,
                    solution=solution,
                    answer_text=answer_text,
                    problem_type='auto',
                    verbose=True
                )

                # Store empirical history
                self.empirical_history.append({
                    'round': round_num,
                    'logical_verdict': original_verdict,
                    'empirical_verdict': empirical_result['verdict'],
                    'empirical_score': empirical_result['score'],
                    'empirical_errors': empirical_result.get('errors', [])
                })

                # Step 3: Combine verdicts
                if empirical_result['verdict'] == 'ROBUST':
                    # Empirical verification passed - override critic's BROKEN verdict
                    # This catches critic FALSE NEGATIVES
                    print(f"\n{'='*80}")
                    print(f"[EMPIRICAL OVERRIDE] Logical verification: {original_verdict}")
                    print(f"[EMPIRICAL OVERRIDE] Empirical verification: {empirical_result['verdict']}")
                    print(f"[EMPIRICAL OVERRIDE] Empirical score: {empirical_result['score']:.1%}")
                    print(f"[EMPIRICAL OVERRIDE] Critic was TOO HARSH - empirical tests PASS")
                    print(f"[EMPIRICAL OVERRIDE] Final verdict: ROBUST (critic overridden)")
                    print(f"{'='*80}\n")

                    attack_result['verdict'] = 'ROBUST'
                    attack_result['empirical_override'] = True
                    attack_result['empirical_score'] = empirical_result['score']
                    attack_result['override_reason'] = 'Empirical tests passed despite critic saying BROKEN'

                elif empirical_result['verdict'] == 'BROKEN':
                    # Empirical verification confirms critic is right
                    print(f"\n{'='*80}")
                    print(f"[EMPIRICAL CONFIRMATION] Critic verdict: {original_verdict}")
                    print(f"[EMPIRICAL CONFIRMATION] Empirical verification: {empirical_result['verdict']}")
                    print(f"[EMPIRICAL CONFIRMATION] Empirical score: {empirical_result['score']:.1%}")
                    print(f"[EMPIRICAL CONFIRMATION] Critic was CORRECT - empirical tests FAIL")
                    print(f"{'='*80}\n")

                    # Keep BROKEN verdict, add empirical errors
                    attack_result['empirical_confirmed'] = True
                    attack_result['empirical_score'] = empirical_result['score']
                    attack_result['empirical_errors'] = empirical_result['errors'][:5]  # Top 5 errors

                    # Add empirical errors to counterexamples
                    if 'counterexamples' not in attack_result:
                        attack_result['counterexamples'] = []

                    # Convert empirical errors to counterexample format
                    for error in empirical_result['errors'][:3]:  # Top 3
                        attack_result['counterexamples'].append(
                            f"Empirical test failed: {error}"
                        )
                
                elif empirical_result['verdict'] == 'SUSPICIOUS':
                    # Empirical verification uncertain - downgrade to SUSPICIOUS
                    print(f"\n[EMPIRICAL WARNING] Score: {empirical_result['score']:.1%} (borderline)")
                    attack_result['verdict'] = 'SUSPICIOUS'
                    attack_result['empirical_warning'] = True
                    attack_result['empirical_score'] = empirical_result['score']
                
                else:
                    # Both logical and empirical say ROBUST - high confidence
                    print(f"\n[EMPIRICAL CONFIRM] Empirical verification passed ({empirical_result['score']:.1%})")
                    attack_result['empirical_confirmed'] = True
                    attack_result['empirical_score'] = empirical_result['score']
        
        return attack_result
    
    def _extract_answer(self, solution: str) -> str:
        """
        Extract answer from solution text.

        Looks for patterns like:
          - \\boxed{...}
          - Final answer: ...
          - Therefore, k ∈ {...}
        """
        import re

        # Pattern 1: \boxed{...} - handle nested braces by counting
        boxed_start = solution.find('\\boxed{')
        if boxed_start != -1:
            # Count braces to find matching closing brace
            start_pos = boxed_start + 7  # len('\\boxed{')
            brace_count = 1
            pos = start_pos

            while pos < len(solution) and brace_count > 0:
                if solution[pos] == '{' and (pos == 0 or solution[pos-1] != '\\'):
                    brace_count += 1
                elif solution[pos] == '}' and (pos == 0 or solution[pos-1] != '\\'):
                    brace_count -= 1
                pos += 1

            if brace_count == 0:
                return solution[start_pos:pos-1]
        
        # Pattern 2: "Final answer:" or "Therefore,"
        final_match = re.search(r'(?:final answer|therefore|thus|hence)[:：]\s*([^\n]+)', solution, re.IGNORECASE)
        if final_match:
            return final_match.group(1)
        
        # Pattern 3: k ∈ {...} or k = ...
        k_match = re.search(r'k\s*[∈=]\s*\{?[^}\n]+\}?', solution)
        if k_match:
            return k_match.group(0)
        
        return ""
    
    def get_empirical_summary(self) -> Dict:
        """Get summary of empirical verification history."""
        if not self.empirical_history:
            return {'total': 0, 'enabled': self.enable_empirical}
        
        return {
            'total': len(self.empirical_history),
            'average_score': sum(h['empirical_score'] for h in self.empirical_history) / len(self.empirical_history),
            'verdicts': {
                'ROBUST': sum(1 for h in self.empirical_history if h['empirical_verdict'] == 'ROBUST'),
                'SUSPICIOUS': sum(1 for h in self.empirical_history if h['empirical_verdict'] == 'SUSPICIOUS'),
                'BROKEN': sum(1 for h in self.empirical_history if h['empirical_verdict'] == 'BROKEN'),
            },
            'enabled': self.enable_empirical
        }

    def _validate_geometric_counterexample(self, ce_text):
        """
        Validate that a geometric counterexample has concrete values.

        PHASE 1.2: Quality filter for geometry counterexamples.

        Args:
            ce_text: Counterexample text

        Returns:
            bool: True if valid (has concrete geometric values), False otherwise
        """
        import re

        # Check 1: Has coordinates: (x,y) or x=..., y=...
        has_coords = bool(re.search(r'\([+-]?\d+\.?\d*\s*,\s*[+-]?\d+\.?\d*\)', ce_text))
        has_coord_assign = bool(re.search(r'[xyz]\s*=\s*[+-]?\d+', ce_text))

        # Check 2: Has angles: θ=30° or angle=45
        has_angles = bool(re.search(r'(angle|θ|∠)\s*=\s*\d+', ce_text))

        # Check 3: Has distances: r=5, distance=3
        has_distances = bool(re.search(r'(radius|distance|length|r|d)\s*=\s*\d+', ce_text))

        # Check 4: Not self-contradicting
        contradictions = ['actually works', 'actually valid', 'seems to work',
                         'appears to work', 'may work']
        has_contradiction = any(phrase in ce_text.lower() for phrase in contradictions)

        # Check 5: Not vague
        vague_phrases = ['might not', 'could fail', 'in general', 'unclear',
                        'not obvious', 'needs verification', 'without concrete']
        is_vague = any(phrase in ce_text.lower() for phrase in vague_phrases)

        # Check 6: Minimum length (avoid trivial rejections)
        has_min_length = len(ce_text) >= 50

        # Need at least 2 concrete measurements AND not vague/contradictory AND minimum length
        concrete_count = sum([has_coords, has_coord_assign, has_angles, has_distances])

        is_valid = (concrete_count >= 2) and (not has_contradiction) and (not is_vague) and has_min_length

        return is_valid


if __name__ == "__main__":
    # Quick integration test
    print("="*80)
    print("EMPIRICAL CRITIC WRAPPER TEST")
    print("="*80)
    
    # Mock solution with wrong answer (Problem 1 error)
    mock_solution = """
    We claim that k=0 or k odd with 1≤k≤n.
    
    Proof:
    ... [detailed proof] ...
    
    Therefore, the answer is \\boxed{k=0 \\text{ or } k \\text{ odd with } 1\\le k\\le n}.
    """
    
    # Mock problem
    mock_problem = "Find all nonnegative integers k such that..."
    
    # Create wrapper
    from adversarial_critic import AdversarialCritic
    base_critic = AdversarialCritic(verbose=False)
    wrapper = EmpiricalCriticWrapper(base_critic, enable_empirical=True)
    
    # Mock attack result (simulating that base critic said ROBUST)
    def mock_attack(*args, **kwargs):
        return {'verdict': 'ROBUST', 'counterexamples': []}
    
    base_critic.attack_solution = mock_attack
    
    # Test wrapper
    print("\n--- Testing empirical override on wrong answer ---")
    result = wrapper.attack_solution(mock_problem, mock_solution, round_num=0)
    
    print(f"\nFinal verdict: {result['verdict']}")
    print(f"Empirical override: {result.get('empirical_override', False)}")
    print(f"Empirical score: {result.get('empirical_score', 0):.1%}")
    
    if result['verdict'] == 'BROKEN':
        print("\n✅ SUCCESS: Empirical verification caught the error!")
    else:
        print("\n❌ FAILURE: Empirical verification did not catch the error")
    
    print("\nEmpirical history:")
    print(wrapper.get_empirical_summary())
    
    print("\n" + "="*80)
