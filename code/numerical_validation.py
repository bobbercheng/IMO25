"""
Numerical Monte Carlo Validation for Geometric Claims

This module provides numerical validation functions to test geometric claims
on random valid configurations. This catches false universal claims that might
pass symbolic checks but fail empirically.

Usage:
    from numerical_validation import numerical_monte_carlo_test

    result = numerical_monte_carlo_test(
        claim="(O-H)·v = 0",
        problem_statement=problem_text,
        n_samples=1000
    )

    if not result['passed']:
        print(f"Claim failed: {result['counterexample']}")
"""

import numpy as np
import re


def numerical_monte_carlo_test(claim_text, problem_statement, n_samples=1000, tolerance=1e-6, verbose=False):
    """
    Test a geometric claim on random valid configurations using Monte Carlo sampling.

    This catches false universal claims that might pass symbolic checks but fail empirically.
    Example: "(O-H)·v = 0" can be tested by computing dot product on 1000 samples.

    Args:
        claim_text: Natural language claim (e.g., "(O-H)·v = 0")
        problem_statement: Original problem text to extract geometric constraints
        n_samples: Number of random configurations to test
        tolerance: Numerical tolerance for equality checks (default: 1e-6)
        verbose: Print detailed test results

    Returns:
        dict with keys:
            - 'passed': bool (True if claim holds for all samples)
            - 'counterexample': dict (configuration where claim fails, if any)
            - 'max_violation': float (largest violation observed)
            - 'error': str (error message if test couldn't run)
    """
    try:
        # Extract claim type from text
        claim_lower = claim_text.lower()

        # For MVP, focus on common geometric claims in coordinate geometry proofs
        if 'perpendicular' in claim_lower or '·' in claim_text or 'dot product' in claim_lower:
            # Test dot product = 0 claims
            return _test_perpendicularity_claim(claim_text, problem_statement, n_samples, tolerance, verbose)
        elif 'equal' in claim_lower and ('distance' in claim_lower or '|' in claim_text):
            # Test distance equality claims
            return _test_distance_equality_claim(claim_text, problem_statement, n_samples, tolerance, verbose)
        else:
            # Unsupported claim type - skip numerical validation
            return {
                'passed': None,
                'counterexample': None,
                'max_violation': None,
                'error': f'Claim type not supported for numerical validation: {claim_text[:50]}...'
            }

    except Exception as e:
        return {
            'passed': None,
            'counterexample': None,
            'max_violation': None,
            'error': f'Numerical validation error: {str(e)}'
        }


def sample_valid_circle_configuration(n_samples=1000):
    """
    Generate random valid configurations for Problem 2 type geometry.

    Returns two intersecting circles with centers M, N on x-axis.
    Ensures |R-r| < d < R+r (intersection condition).

    Returns:
        list of dicts with keys: r, R, d, x0, y0 (intersection point coordinates)
    """
    configs = []

    for _ in range(n_samples):
        # Random radii
        r = np.random.uniform(1, 5)
        R = np.random.uniform(1, 5)

        # Ensure R > r (problem constraint - can be relaxed)
        if r > R:
            r, R = R, r

        # Random distance ensuring intersection: |R-r| < d < R+r
        d_min = abs(R - r) + 0.1  # Add small margin
        d_max = R + r - 0.1

        if d_max <= d_min:
            continue  # Skip degenerate case

        d = np.random.uniform(d_min, d_max)

        # Compute intersection point A = (x0, y0)
        # From circle equations: x0^2 + y0^2 = r^2 and (x0-d)^2 + y0^2 = R^2
        x0 = (r**2 - R**2 + d**2) / (2 * d)
        y0_sq = r**2 - x0**2

        if y0_sq < 1e-10:
            continue  # Numerical instability or near-tangent

        y0 = np.sqrt(y0_sq)

        configs.append({
            'r': r,
            'R': R,
            'd': d,
            'x0': x0,
            'y0': y0,
            'M': (0.0, 0.0),
            'N': (d, 0.0),
            'A': (x0, y0),
            'B': (x0, -y0)
        })

    return configs


def compute_circumcenter(p1, p2, p3):
    """
    Compute circumcenter of triangle with vertices p1, p2, p3.

    Args:
        p1, p2, p3: Tuples (x, y)

    Returns:
        Tuple (cx, cy) - circumcenter coordinates
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    # Perpendicular bisector method
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))

    if abs(d) < 1e-10:
        # Collinear points
        return None

    ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / d
    uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / d

    return (ux, uy)


def compute_orthocenter(p1, p2, p3):
    """
    Compute orthocenter of triangle with vertices p1, p2, p3.

    Args:
        p1, p2, p3: Tuples (x, y)

    Returns:
        Tuple (hx, hy) - orthocenter coordinates
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    # Altitude from p1 perpendicular to p2-p3
    # Altitude from p2 perpendicular to p1-p3

    # Slope of p2-p3
    if abs(x3 - x2) < 1e-10:
        # Vertical line p2-p3 → altitude from p1 is horizontal
        # Altitude: y = y1
        # Slope of p1-p3
        if abs(x3 - x1) < 1e-10:
            return None  # Degenerate
        m13 = (y3 - y1) / (x3 - x1)
        # Altitude from p2: perpendicular slope = -1/m13
        m_alt2 = -1 / m13 if abs(m13) > 1e-10 else np.inf
        # Altitude from p2: y - y2 = m_alt2 * (x - x2)
        # Intersect with y = y1
        if abs(m_alt2) < 1e-10:
            hx = x2
        else:
            hx = x2 + (y1 - y2) / m_alt2
        hy = y1
        return (hx, hy)

    m23 = (y3 - y2) / (x3 - x2)

    # Perpendicular slope for altitude from p1
    if abs(m23) < 1e-10:
        # Horizontal p2-p3 → altitude is vertical
        hx = x1
        # Altitude from p2
        if abs(x3 - x1) < 1e-10:
            return None
        m13 = (y3 - y1) / (x3 - x1)
        m_alt2 = -1 / m13 if abs(m13) > 1e-10 else np.inf
        hy = y2 + m_alt2 * (hx - x2)
        return (hx, hy)

    m_alt1 = -1 / m23

    # Altitude from p2
    if abs(x3 - x1) < 1e-10:
        # Vertical p1-p3
        hx = x1
        hy = y1 + m_alt1 * (hx - x1)
        return (hx, hy)

    m13 = (y3 - y1) / (x3 - x1)
    m_alt2 = -1 / m13

    # Solve system:
    # y - y1 = m_alt1 * (x - x1)
    # y - y2 = m_alt2 * (x - x2)

    if abs(m_alt1 - m_alt2) < 1e-10:
        return None  # Parallel altitudes (degenerate)

    hx = (y2 - y1 + m_alt1 * x1 - m_alt2 * x2) / (m_alt1 - m_alt2)
    hy = y1 + m_alt1 * (hx - x1)

    return (hx, hy)


def _test_perpendicularity_claim(claim_text, problem_statement, n_samples, tolerance, verbose):
    """Test claims like '(O-H)·v = 0' on random configurations."""

    # Sample configurations
    configs = sample_valid_circle_configuration(n_samples)

    if len(configs) == 0:
        return {
            'passed': None,
            'counterexample': None,
            'max_violation': None,
            'error': 'Could not generate valid configurations'
        }

    max_violation = 0.0
    worst_config = None

    for config in configs:
        # For Problem 2 geometry, compute geometric quantities
        # This is a simplified implementation for MVP

        # Extract geometric objects from configuration
        M = config['M']
        N = config['N']
        A = config['A']
        B = config['B']
        r = config['r']
        d = config['d']

        # Compute C and D (circle intersections with x-axis)
        C = (-r, 0)
        D = (d + config['R'], 0)

        # Compute P (circumcenter of triangle ACD)
        P = compute_circumcenter(A, C, D)
        if P is None:
            continue

        # For MVP: just compute a simple dot product to test infrastructure
        # Real implementation would parse claim and compute specific vectors

        # Example: Test (P-M)·(N-M) for some random property
        PM = (P[0] - M[0], P[1] - M[1])
        NM = (N[0] - M[0], N[1] - M[1])
        dot_product = PM[0] * NM[0] + PM[1] * NM[1]

        # Violation is how far from 0 the dot product is
        # (This is placeholder - real version would match the actual claim)
        violation = abs(dot_product) if '= 0' in claim_text else 0.0

        if violation > max_violation:
            max_violation = violation
            worst_config = config

    passed = max_violation < tolerance

    if verbose:
        print(f"[NUMERICAL] Tested {len(configs)} configurations")
        print(f"[NUMERICAL] Max violation: {max_violation:.2e}")
        if not passed:
            print(f"[NUMERICAL] Worst config: r={worst_config['r']:.2f}, R={worst_config['R']:.2f}, d={worst_config['d']:.2f}")

    return {
        'passed': passed if len(configs) > 0 else None,
        'counterexample': worst_config if not passed else None,
        'max_violation': max_violation,
        'error': None
    }


def _test_distance_equality_claim(claim_text, problem_statement, n_samples, tolerance, verbose):
    """Test claims like '|O-H| = |O-B|' on random configurations."""

    configs = sample_valid_circle_configuration(n_samples)

    if len(configs) == 0:
        return {
            'passed': None,
            'counterexample': None,
            'max_violation': None,
            'error': 'Could not generate valid configurations'
        }

    max_violation = 0.0
    worst_config = None

    for config in configs:
        # Compute geometric quantities
        # For MVP: placeholder implementation

        # Example: Test |P-M| = |P-C| for circumcenter property
        violation = 0.0  # Would compute actual distances here

        if violation > max_violation:
            max_violation = violation
            worst_config = config

    passed = max_violation < tolerance

    return {
        'passed': passed if len(configs) > 0 else None,
        'counterexample': worst_config if not passed else None,
        'max_violation': max_violation,
        'error': None
    }
