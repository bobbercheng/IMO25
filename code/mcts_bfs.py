"""
MCTS-Enhanced BFS for IMO Problem Solving

This module implements Monte Carlo Tree Search (MCTS) to guide the exploration
of different proof strategies and approaches for mathematical problem solving.
"""

import math
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class MCTSNode:
    """
    Node in the MCTS tree representing a proof strategy/approach.

    Attributes:
        strategy: Description of the proof strategy (e.g., "induction", "contradiction")
        parent: Parent node in the tree
        children: List of child nodes (refined strategies)
        visits: Number of times this node has been visited
        total_score: Cumulative score from all simulations
        solutions: List of solutions generated with this strategy
        best_score: Best score achieved with this strategy
    """

    def __init__(self, strategy: str, parent: Optional['MCTSNode'] = None):
        self.strategy = strategy
        self.parent = parent
        self.children: List['MCTSNode'] = []
        self.visits = 0
        self.total_score = 0.0
        self.solutions: List[Dict] = []
        self.best_score = -999999.0
        self.is_terminal = False

        # Track proof techniques and patterns
        self.techniques_used = []
        self.common_errors = []

    def add_child(self, strategy: str) -> 'MCTSNode':
        """Add a child node with the given strategy."""
        child = MCTSNode(strategy, parent=self)
        self.children.append(child)
        return child

    def update(self, score: float, solution: Dict):
        """Update node statistics with a new simulation result."""
        self.visits += 1
        self.total_score += score
        self.solutions.append(solution)

        if score > self.best_score:
            self.best_score = score

        print(f">>>>>>> [MCTS] Updated node '{self.strategy}': visits={self.visits}, avg_score={self.avg_score():.2f}, best={self.best_score:.2f}")

    def avg_score(self) -> float:
        """Calculate average score for this node."""
        if self.visits == 0:
            return 0.0
        return self.total_score / self.visits

    def ucb1(self, exploration_constant: float = 1.414) -> float:
        """
        Calculate UCB1 (Upper Confidence Bound) score for node selection.

        UCB1 = avg_score + c * sqrt(ln(parent_visits) / visits)

        Args:
            exploration_constant: Controls exploration vs exploitation tradeoff

        Returns:
            UCB1 score (higher means more promising to explore)
        """
        if self.visits == 0:
            return float('inf')  # Unvisited nodes have infinite priority

        if self.parent is None:
            return self.avg_score()

        exploitation = self.avg_score()
        exploration = exploration_constant * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )

        return exploitation + exploration

    def to_dict(self) -> Dict:
        """Convert node to dictionary for serialization."""
        return {
            'strategy': self.strategy,
            'visits': self.visits,
            'total_score': self.total_score,
            'avg_score': self.avg_score(),
            'best_score': self.best_score,
            'num_solutions': len(self.solutions),
            'children': [child.to_dict() for child in self.children]
        }


class MCTSExplorer:
    """
    MCTS-based exploration manager for proof strategy selection.

    Uses Monte Carlo Tree Search to intelligently explore different
    proof approaches and refine promising strategies.
    """

    def __init__(self, exploration_constant: float = 1.414, max_depth: int = 3,
                 enable_hybrids: bool = True, problem_type: Optional[str] = None):
        """
        Initialize MCTS explorer.

        Args:
            exploration_constant: UCB1 exploration parameter
            max_depth: Maximum tree depth
            enable_hybrids: Whether to enable hybrid strategy generation (Tier 2 optimization)
            problem_type: Optional problem type hint for strategy prioritization
        """
        self.root = MCTSNode("root")
        self.exploration_constant = exploration_constant
        self.max_depth = max_depth
        self.total_simulations = 0
        self.enable_hybrids = enable_hybrids
        self.problem_type = problem_type

        # Track strategy performance across simulations for adaptive selection
        self.strategy_performance = {}

        # Initialize strategy tree with common proof techniques
        self._initialize_strategy_tree()

        print(f">>>>>>> [MCTS] Initialized with exploration_constant={exploration_constant}, max_depth={max_depth}")
        print(f">>>>>>> [MCTS] Hybrid strategies: {'enabled' if enable_hybrids else 'disabled'}")
        if problem_type:
            print(f">>>>>>> [MCTS] Problem type hint: {problem_type}")

    def _initialize_strategy_tree(self):
        """Initialize root node with common proof strategies and hybrid approaches."""
        common_strategies = [
            "Mathematical induction",
            "Direct proof / construction",
            "Proof by contradiction",
            "Pigeonhole principle",
            "Combinatorial argument",
            "Algebraic manipulation",
            "Geometric insight",
            "Extremal principle"
        ]

        # Tier 2 optimization: Enable hybrid strategies for better exploration
        hybrid_strategies = []
        if self.enable_hybrids:
            hybrid_strategies = [
                "Induction with extremal principle",
                "Contradiction with pigeonhole principle",
                "Construction with algebraic manipulation",
                "Combinatorial with geometric insight",
                "Double counting with algebraic manipulation",
                "Geometric transformation with symmetry"
            ]

        # Problem-type aware strategy prioritization (Tier 2 optimization)
        priority_strategies = []
        if self.problem_type:
            problem_type_lower = self.problem_type.lower()
            if "number" in problem_type_lower or "divisibility" in problem_type_lower:
                priority_strategies = [
                    "Mathematical induction",
                    "Direct proof / construction",
                    "Proof by contradiction"
                ]
            elif "geometry" in problem_type_lower:
                priority_strategies = [
                    "Geometric insight",
                    "Algebraic manipulation",
                    "Geometric transformation with symmetry"
                ]
            elif "combinatorics" in problem_type_lower or "counting" in problem_type_lower:
                priority_strategies = [
                    "Combinatorial argument",
                    "Pigeonhole principle",
                    "Double counting with algebraic manipulation"
                ]
            elif "inequality" in problem_type_lower:
                priority_strategies = [
                    "Algebraic manipulation",
                    "Extremal principle",
                    "Mathematical induction"
                ]

        # Build ordered strategy list: priority first, then others
        all_strategies = []
        for s in priority_strategies:
            if s not in all_strategies:
                all_strategies.append(s)
        for s in common_strategies:
            if s not in all_strategies:
                all_strategies.append(s)
        for s in hybrid_strategies:
            if s not in all_strategies:
                all_strategies.append(s)

        for strategy in all_strategies:
            self.root.add_child(strategy)

        config_type = "hybrid-enabled" if self.enable_hybrids else "baseline"
        print(f">>>>>>> [MCTS] Initialized with {len(all_strategies)} strategies ({config_type} configuration)")

    def select(self) -> MCTSNode:
        """
        Selection phase: Navigate tree using UCB1 to find most promising leaf.

        Returns:
            Selected leaf node for expansion/simulation
        """
        node = self.root
        depth = 0

        print(f">>>>>>> [MCTS] Selection phase starting from root")

        while node.children and depth < self.max_depth:
            # Select child with highest UCB1 score
            node = max(node.children, key=lambda n: n.ucb1(self.exploration_constant))
            depth += 1
            print(f">>>>>>> [MCTS] Selected '{node.strategy}' (UCB1={node.ucb1():.3f}, depth={depth})")

        return node

    def expand(self, node: MCTSNode) -> MCTSNode:
        """
        Expansion phase: Add child nodes for unexplored strategies.

        If node has been visited and isn't at max depth, expand with
        refined/hybrid strategies.

        Args:
            node: Node to expand

        Returns:
            Newly created child node (or node itself if can't expand)
        """
        if node.visits == 0:
            # Node hasn't been simulated yet, don't expand
            print(f">>>>>>> [MCTS] Node '{node.strategy}' not yet simulated, skipping expansion")
            return node

        if self._get_depth(node) >= self.max_depth:
            # Max depth reached
            print(f">>>>>>> [MCTS] Max depth reached at '{node.strategy}', no expansion")
            return node

        # Generate refined strategies based on parent strategy
        refined_strategies = self._generate_refined_strategies(node)

        if not refined_strategies:
            print(f">>>>>>> [MCTS] No refined strategies for '{node.strategy}'")
            return node

        # Add new children
        new_children = []
        for strategy in refined_strategies:
            child = node.add_child(strategy)
            new_children.append(child)

        print(f">>>>>>> [MCTS] Expanded '{node.strategy}' with {len(new_children)} refined strategies")

        # Return first new child for simulation
        return new_children[0] if new_children else node

    def simulate(self, node: MCTSNode, problem_statement: str,
                 generate_solution_func, verify_solution_func,
                 sol_reasoning: str, self_imp_reasoning: str, ver_reasoning: str) -> Tuple[float, Dict]:
        """
        Simulation phase: Generate solution using node's strategy.

        Args:
            node: Node representing strategy to simulate
            problem_statement: Mathematical problem to solve
            generate_solution_func: Function to generate solution
            verify_solution_func: Function to verify solution
            sol_reasoning: Solution reasoning level
            self_imp_reasoning: Self-improvement reasoning level
            ver_reasoning: Verification reasoning level

        Returns:
            (score, solution_dict) tuple
        """
        print(f">>>>>>> [MCTS] Simulating strategy '{node.strategy}'")

        # Create strategy-specific prompt
        strategy_prompt = f"\n\nIMPORTANT: Use the following proof strategy: {node.strategy}"

        try:
            # Generate solution with strategy guidance
            p1, solution, verify, good_verify = generate_solution_func(
                problem_statement,
                True,  # verbose
                [strategy_prompt],  # other_prompts
                sol_reasoning,
                self_imp_reasoning,
                ver_reasoning
            )

            if solution is None:
                print(f">>>>>>> [MCTS] Simulation failed - no solution generated")
                return -999999.0, {}

            # Calculate score
            score = self._calculate_score(verify, good_verify)

            solution_dict = {
                'solution': solution,
                'verify': verify,
                'good_verify': good_verify,
                'score': score,
                'strategy': node.strategy,
                'timestamp': datetime.now().isoformat()
            }

            print(f">>>>>>> [MCTS] Simulation result: score={score:.2f}, passed={good_verify}")

            return score, solution_dict

        except Exception as e:
            print(f">>>>>>> [MCTS] Simulation failed with error: {e}")
            return -999999.0, {}

    def backpropagate(self, node: MCTSNode, score: float, solution: Dict):
        """
        Backpropagation phase: Update node and all ancestors with simulation result.

        Args:
            node: Leaf node where simulation occurred
            score: Score achieved in simulation
            solution: Solution dictionary
        """
        print(f">>>>>>> [MCTS] Backpropagating score={score:.2f} from '{node.strategy}'")

        current = node
        depth = 0

        while current is not None:
            current.update(score, solution)
            print(f">>>>>>> [MCTS] Updated '{current.strategy}' at depth {depth}")
            current = current.parent
            depth += 1

    def search(self, problem_statement: str, num_simulations: int,
               generate_solution_func, verify_solution_func,
               sol_reasoning: str, self_imp_reasoning: str, ver_reasoning: str) -> Tuple[Dict, List[Dict]]:
        """
        Run MCTS search for the given number of simulations.

        Args:
            problem_statement: Mathematical problem to solve
            num_simulations: Number of MCTS iterations to perform
            generate_solution_func: Function to generate solutions
            verify_solution_func: Function to verify solutions
            sol_reasoning: Solution reasoning level
            self_imp_reasoning: Self-improvement reasoning level
            ver_reasoning: Verification reasoning level

        Returns:
            Tuple of (best_solution, all_solutions_sorted_by_score)
        """
        print(f">>>>>>> [MCTS] Starting search with {num_simulations} simulations")
        print(f">>>>>>> [MCTS] Reasoning levels: solution={sol_reasoning}, self_imp={self_imp_reasoning}, verification={ver_reasoning}")

        best_solution = None
        best_score = -999999.0
        all_solutions = []  # Collect all solutions for Best-of-N

        for sim_num in range(num_simulations):
            print(f"\n>>>>>>> [MCTS] ===== Simulation {sim_num + 1}/{num_simulations} =====")

            # MCTS phases
            selected_node = self.select()
            expanded_node = self.expand(selected_node)
            score, solution = self.simulate(
                expanded_node, problem_statement,
                generate_solution_func, verify_solution_func,
                sol_reasoning, self_imp_reasoning, ver_reasoning
            )
            self.backpropagate(expanded_node, score, solution)

            # Collect solution if valid
            if solution and 'solution' in solution:
                all_solutions.append(solution)

            # Track best solution
            if score > best_score:
                best_score = score
                best_solution = solution
                print(f">>>>>>> [MCTS] New best solution! Score: {best_score:.2f}, Strategy: '{expanded_node.strategy}'")

            self.total_simulations += 1

        # Sort all solutions by score (descending)
        all_solutions_sorted = sorted(all_solutions, key=lambda s: s.get('score', -999999), reverse=True)

        print(f"\n>>>>>>> [MCTS] Search complete. Best score: {best_score:.2f}")
        print(f">>>>>>> [MCTS] Best strategy: {best_solution.get('strategy', 'unknown') if best_solution else 'none'}")
        print(f">>>>>>> [MCTS] Total valid solutions collected: {len(all_solutions_sorted)}")

        return best_solution, all_solutions_sorted

    def get_best_strategies(self, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Get top-k strategies by average score.

        Args:
            top_k: Number of top strategies to return

        Returns:
            List of (strategy, avg_score) tuples
        """
        all_nodes = self._collect_all_nodes()
        visited_nodes = [n for n in all_nodes if n.visits > 0]

        sorted_nodes = sorted(visited_nodes, key=lambda n: n.avg_score(), reverse=True)

        return [(n.strategy, n.avg_score()) for n in sorted_nodes[:top_k]]

    def save_tree(self, filepath: str):
        """Save MCTS tree to JSON file with full state for resume capability."""
        tree_data = {
            'total_simulations': self.total_simulations,
            'exploration_constant': self.exploration_constant,
            'max_depth': self.max_depth,
            'enable_hybrids': self.enable_hybrids,
            'problem_type': self.problem_type,
            'strategy_performance': self.strategy_performance,
            'tree': self.root.to_dict(),
            'timestamp': datetime.now().isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(tree_data, f, indent=2)

        print(f">>>>>>> [MCTS] Tree saved to {filepath}")

    @classmethod
    def load_tree(cls, filepath: str) -> Optional['MCTSExplorer']:
        """
        Load MCTS tree from JSON file for resume capability (Tier 2 optimization).

        Args:
            filepath: Path to saved tree JSON

        Returns:
            MCTSExplorer instance with restored state, or None if load fails
        """
        try:
            with open(filepath, 'r') as f:
                tree_data = json.load(f)

            # Create explorer with saved config
            explorer = cls(
                exploration_constant=tree_data.get('exploration_constant', 1.414),
                max_depth=tree_data.get('max_depth', 3),
                enable_hybrids=tree_data.get('enable_hybrids', True),
                problem_type=tree_data.get('problem_type')
            )

            # Restore state
            explorer.total_simulations = tree_data.get('total_simulations', 0)
            explorer.strategy_performance = tree_data.get('strategy_performance', {})

            # Rebuild tree from saved data
            def rebuild_node(node_data: Dict, parent: Optional[MCTSNode] = None) -> MCTSNode:
                node = MCTSNode(node_data['strategy'], parent=parent)
                node.visits = node_data.get('visits', 0)
                node.total_score = node_data.get('total_score', 0.0)
                node.best_score = node_data.get('best_score', -999999.0)

                for child_data in node_data.get('children', []):
                    child = rebuild_node(child_data, parent=node)
                    node.children.append(child)

                return node

            # Rebuild root and tree structure
            if 'tree' in tree_data:
                explorer.root = rebuild_node(tree_data['tree'])

            print(f">>>>>>> [MCTS] Tree loaded from {filepath}")
            print(f">>>>>>> [MCTS] Restored {explorer.total_simulations} simulations")

            return explorer

        except FileNotFoundError:
            print(f">>>>>>> [MCTS] No saved tree found at {filepath}")
            return None
        except Exception as e:
            print(f">>>>>>> [MCTS] Error loading tree: {e}")
            return None

    def _calculate_score(self, verify: str, good_verify: str) -> float:
        """
        Calculate score from verification results with granular feedback (Tier 2 optimization).

        Scoring breakdown:
        - Perfect verification ("yes"): +100 base points
        - Critical errors: -15 points each
        - Justification gaps: -8 points each
        - Minor issues: -3 points each
        - Partial correctness indicators: +20-50 points
        - Shorter bug reports (fewer issues): bonus points
        """
        score = 0.0

        # Perfect verification
        if good_verify and "yes" in good_verify.lower():
            score += 100.0

        if verify:
            verify_lower = verify.lower()

            # Count different error types with nuanced weighting
            critical_errors = verify_lower.count('critical error') + verify_lower.count('critical flaw')
            justification_gaps = verify_lower.count('justification gap') + verify_lower.count('missing justification')
            minor_issues = verify_lower.count('minor issue') + verify_lower.count('minor error')
            major_issues = verify_lower.count('major issue') + verify_lower.count('significant error')

            score -= critical_errors * 15
            score -= major_issues * 10
            score -= justification_gaps * 8
            score -= minor_issues * 3

            # Partial correctness bonuses (Tier 2 optimization)
            if "mostly correct" in verify_lower or "partially correct" in verify_lower:
                score += 30.0
            if "correct approach" in verify_lower or "right direction" in verify_lower:
                score += 20.0
            if "key insight" in verify_lower and "correct" in verify_lower:
                score += 25.0

            # Penalize/reward based on verification length (proxy for number of issues)
            # Shorter verifications with "yes" = clean solution
            # Long verifications = many issues
            verification_length_penalty = min(len(verify) / 200, 20)  # Cap at 20 points penalty
            score -= verification_length_penalty

            # Bonus for explicit positive mentions
            if "correct" in verify_lower and critical_errors == 0:
                score += 15.0
            if "valid" in verify_lower or "sound" in verify_lower:
                score += 10.0
        else:
            # No verification text - assume no errors found
            score += 50.0

        # Track strategy performance for adaptive selection
        return score

    def _get_depth(self, node: MCTSNode) -> int:
        """Get depth of node in tree."""
        depth = 0
        current = node
        while current.parent is not None:
            depth += 1
            current = current.parent
        return depth

    def _collect_all_nodes(self) -> List[MCTSNode]:
        """Collect all nodes in tree (BFS traversal)."""
        nodes = []
        queue = [self.root]

        while queue:
            node = queue.pop(0)
            nodes.append(node)
            queue.extend(node.children)

        return nodes

    def _generate_refined_strategies(self, node: MCTSNode) -> List[str]:
        """
        Generate refined/hybrid strategies based on parent strategy.

        Args:
            node: Parent node

        Returns:
            List of refined strategy descriptions
        """
        strategy = node.strategy.lower()

        refinements = []

        # Strategy-specific refinements
        if "induction" in strategy:
            refinements = [
                "Strong induction with multiple base cases",
                "Induction with extremal principle",
                "Backward induction"
            ]
        elif "contradiction" in strategy:
            refinements = [
                "Contradiction with minimal counterexample",
                "Contradiction with extremal principle",
                "Contradiction combined with pigeonhole"
            ]
        elif "construction" in strategy or "direct" in strategy:
            refinements = [
                "Explicit construction with induction",
                "Greedy construction algorithm",
                "Constructive proof with uniqueness"
            ]
        elif "pigeonhole" in strategy:
            refinements = [
                "Generalized pigeonhole principle",
                "Pigeonhole with extremal argument",
                "Pigeonhole with counting"
            ]
        elif "combinatorial" in strategy:
            refinements = [
                "Bijective proof",
                "Double counting argument",
                "Inclusion-exclusion principle"
            ]
        elif "algebraic" in strategy:
            refinements = [
                "Polynomial manipulation with roots",
                "Algebraic inequalities (AM-GM, Cauchy-Schwarz)",
                "Algebraic symmetry exploitation"
            ]
        elif "geometric" in strategy:
            refinements = [
                "Coordinate geometry approach",
                "Geometric transformations",
                "Geometric inequalities"
            ]
        elif "extremal" in strategy:
            refinements = [
                "Extremal principle with construction",
                "Extremal principle with contradiction",
                "Min-max argument"
            ]

        # If at root or no specific refinements, generate hybrid strategies
        if not refinements and node.children:
            # Create hybrid strategies from successful children
            successful_children = [c for c in node.children if c.avg_score() > 60]
            if len(successful_children) >= 2:
                # Generate multiple hybrid combinations from top performers
                refinements = []
                for i in range(min(2, len(successful_children) - 1)):
                    refinements.append(
                        f"Hybrid: {successful_children[i].strategy} + {successful_children[i+1].strategy}"
                    )
                # Also try combining the best with the third-best for diversity
                if len(successful_children) >= 3:
                    refinements.append(
                        f"Hybrid: {successful_children[0].strategy} + {successful_children[2].strategy}"
                    )

        return refinements


def mcts_bfs_search(problem_statement: str, num_simulations: int,
                   generate_solution_func, verify_solution_func,
                   sol_reasoning: str = "low",
                   self_imp_reasoning: str = "high",
                   ver_reasoning: str = "high",
                   exploration_constant: float = 1.414,
                   max_depth: int = 2,
                   save_tree_path: Optional[str] = None,
                   best_of_n: int = 0,
                   enable_hybrids: bool = True,
                   problem_type: Optional[str] = None,
                   resume_from_tree: Optional[str] = None) -> Optional[Dict]:
    """
    Perform MCTS-guided BFS exploration for mathematical problem solving.

    Args:
        problem_statement: Problem to solve
        num_simulations: Number of MCTS simulations (default: 5, baseline proven config)
        generate_solution_func: Solution generation function (init_explorations)
        verify_solution_func: Solution verification function
        sol_reasoning: Solution generation reasoning level (default: "low")
        self_imp_reasoning: Self-improvement reasoning level (default: "high")
        ver_reasoning: Verification reasoning level (default: "high")
        exploration_constant: UCB1 exploration parameter (default: 1.414, sqrt(2) baseline)
        max_depth: Maximum tree depth (default: 2, baseline proven config)
        save_tree_path: Path to save MCTS tree (optional)
        best_of_n: If > 0, verify top N solutions and return first verified (default: 0)
        enable_hybrids: Enable hybrid strategy generation (Tier 2 optimization, default: True)
        problem_type: Optional problem type hint for strategy prioritization (Tier 2 optimization)
        resume_from_tree: Path to saved tree for resume capability (Tier 2 optimization)

    Returns:
        Best solution dictionary or None if no solution found
    """
    print(f"\n{'='*80}")
    print(f">>>>>>> [MCTS-BFS] Starting MCTS-guided exploration")
    print(f">>>>>>> [MCTS-BFS] Simulations: {num_simulations}")
    print(f">>>>>>> [MCTS-BFS] Reasoning: {sol_reasoning}/{self_imp_reasoning}/{ver_reasoning}")
    print(f">>>>>>> [MCTS-BFS] Exploration constant: {exploration_constant}")
    print(f">>>>>>> [MCTS-BFS] Max depth: {max_depth}")
    print(f">>>>>>> [MCTS-BFS] Hybrid strategies: {'enabled' if enable_hybrids else 'disabled'}")
    if problem_type:
        print(f">>>>>>> [MCTS-BFS] Problem type: {problem_type}")
    if resume_from_tree:
        print(f">>>>>>> [MCTS-BFS] Resuming from: {resume_from_tree}")
    print(f"{'='*80}\n")

    # Try to resume from saved tree if provided (Tier 2 optimization)
    explorer = None
    if resume_from_tree:
        explorer = MCTSExplorer.load_tree(resume_from_tree)
        if explorer:
            print(f">>>>>>> [MCTS-BFS] Resumed from saved tree with {explorer.total_simulations} prior simulations")

    # Initialize fresh MCTS explorer if no resume or resume failed
    if explorer is None:
        explorer = MCTSExplorer(
            exploration_constant=exploration_constant,
            max_depth=max_depth,
            enable_hybrids=enable_hybrids,
            problem_type=problem_type
        )

    # Run MCTS search
    best_solution, all_solutions = explorer.search(
        problem_statement=problem_statement,
        num_simulations=num_simulations,
        generate_solution_func=generate_solution_func,
        verify_solution_func=verify_solution_func,
        sol_reasoning=sol_reasoning,
        self_imp_reasoning=self_imp_reasoning,
        ver_reasoning=ver_reasoning
    )

    # Print best strategies
    print(f"\n{'='*80}")
    print(f">>>>>>> [MCTS-BFS] Top strategies by average score:")
    top_strategies = explorer.get_best_strategies(top_k=5)
    for idx, (strategy, avg_score) in enumerate(top_strategies, 1):
        print(f">>>>>>> [MCTS-BFS]   {idx}. {strategy}: {avg_score:.2f}")
    print(f"{'='*80}\n")

    # Best-of-N sampling: Try verifying top N solutions
    if best_of_n > 0 and len(all_solutions) > 0:
        print(f"\n{'='*80}")
        print(f">>>>>>> [BEST-OF-N] Enabled with N={best_of_n}")
        print(f">>>>>>> [BEST-OF-N] Verifying top {min(best_of_n, len(all_solutions))} solutions")
        print(f"{'='*80}\n")

        # Take top N solutions by score
        top_n_solutions = all_solutions[:min(best_of_n, len(all_solutions))]

        for idx, solution_dict in enumerate(top_n_solutions, 1):
            print(f"\n>>>>>>> [BEST-OF-N] Verifying solution {idx}/{len(top_n_solutions)}")
            print(f">>>>>>> [BEST-OF-N] Strategy: {solution_dict.get('strategy', 'unknown')}")
            print(f">>>>>>> [BEST-OF-N] Score: {solution_dict.get('score', 0):.2f}")

            # Re-verify with high reasoning to double-check
            solution_text = solution_dict.get('solution', '')
            if solution_text:
                verify_result, good_verify = verify_solution_func(
                    problem_statement,
                    solution_text,
                    reasoning_effort=ver_reasoning
                )

                print(f">>>>>>> [BEST-OF-N] Verification result: {good_verify}")

                if "yes" in good_verify.lower():
                    print(f"\n{'='*80}")
                    print(f">>>>>>> [BEST-OF-N] ✓ VERIFIED SOLUTION FOUND (solution {idx})")
                    print(f">>>>>>> [BEST-OF-N] Strategy: {solution_dict.get('strategy', 'unknown')}")
                    print(f">>>>>>> [BEST-OF-N] Returning verified solution")
                    print(f"{'='*80}\n")

                    # Update solution dict with fresh verification
                    solution_dict['verify'] = verify_result
                    solution_dict['good_verify'] = good_verify

                    # Save tree before returning
                    if save_tree_path:
                        explorer.save_tree(save_tree_path)

                    return solution_dict

        print(f"\n>>>>>>> [BEST-OF-N] No verified solution found in top {len(top_n_solutions)}")
        print(f">>>>>>> [BEST-OF-N] Falling back to best-scoring solution")

    # Save tree if requested
    if save_tree_path:
        explorer.save_tree(save_tree_path)

    return best_solution
