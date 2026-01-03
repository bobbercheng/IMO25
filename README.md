# RLAC Enhancement Research: Bridging the Generator-Verifier Gap

## Overview

This research addresses a critical finding in the IMO25 mathematical reasoning system: **solutions generated with low reasoning effort consistently fail high-reasoning verification**, despite appearing correct during generation.

**Core Problem:** The system achieves 0% verification pass rate because solutions sound good but contain subtle logical errors that only emerge under rigorous checking.

**Research Solution:** RLAC (Reinforcement Learning with Adversarial Critics) enhancements that insert adversarial feedback **during generation**, not just after completion.

---

## Documents in This Research

### 1. **rlac_summary.txt** - Executive Overview
Start here for a quick understanding of the problem and proposed solution.

**Contents:**
- Problem analysis with specific examples from IMO-02
- Current RLAC implementation status (what exists in codebase)
- 6 key enhancement proposals (compact format)
- Expected outcomes and success metrics
- Research conclusion

**Reading time:** 10-15 minutes  
**Best for:** Getting oriented with the gap and high-level solutions

---

### 2. **rlac_gap_analysis.md** - Detailed Research Analysis
Comprehensive technical analysis of the generator-verifier gap and proposed solutions.

**Contents:**
- Problem analysis with root cause explanation
- RLAC enhancement strategy (6 core improvements)
  1. Critic-Assisted Solution Generation (CASG)
  2. Structured Flaw Reporting with Severity & Location
  3. Geometry-Specific Attack Curriculum
  4. Counterexample Generation for Geometric Claims
  5. Defense and Concession Tracking
  6. Confidence Calibration through Adversarial Feedback
- Multi-stage verification pipeline (4 stages)
- Specific enhancements for IMO-02 (tailored critic prompts)
- Implementation roadmap (5 research phases)
- Risk analysis and mitigations
- Theoretical justification
- Example scenario comparison (without vs. with RLAC)

**Reading time:** 30-45 minutes  
**Best for:** Deep technical understanding and implementation planning

---

### 3. **rlac_architecture_comparison.md** - Visual Architecture Guide
Side-by-side comparison of current vs. proposed architectures with detailed workflow examples.

**Contents:**
- Current architecture diagram (sequential pipeline)
- Proposed architecture diagram (integrated with RLAC)
- Side-by-side feature comparison table
- Detailed example from IMO-02 (current vs. proposed approach)
- Attack intensity progression (current vs. geometry-specific)
- Confidence calibration mechanism (with examples)
- Implementation roadmap with 5 phases
- Key architectural principles
- Success criteria for RLAC enhancement

**Reading time:** 20-30 minutes  
**Best for:** Understanding the architectural shift and practical implementation

---

## Key Findings Summary

### The Gap
- **Generator confidence:** "This is a rigorous, complete solution" (99%)
- **Verification finding:** "This has critical errors" (verification fails)
- **Calibration error:** 100%

### Root Cause
No mechanism during generation to challenge weak assumptions. Verification feedback arrives too late—after the solution is already committed to a potentially flawed approach.

### The Fix
Insert adversarial critics **during generation** (outline phase) that:
- Actively try to break solutions
- Provide specific feedback (structured flaws, not binary verdicts)
- Use domain-specific attacks (geometry patterns, theorem preconditions)
- Track how generators respond (defense vs. concession)
- Calibrate confidence (penalize overconfidence)

### Expected Impact
- Verification pass rate: 0% → 40-60%
- Confidence calibration error: 100% → 5-10%
- Early error detection: 0% → 50%+

---

## Quick Reference: 6 Core Enhancements

| # | Enhancement | Current | Proposed | Benefit |
|---|------------|---------|----------|---------|
| 1 | **Timing** | After full solution | During outline phase | Early pivot possible |
| 2 | **Feedback** | Binary (correct/wrong) | Structured (location/fix) | Targeted improvements |
| 3 | **Attacks** | Generic patterns | Geometry-specific | Better error detection |
| 4 | **Examples** | Sometimes vague | Explicit constructions | Clear why claim fails |
| 5 | **Tracking** | Verdict only | Defense vs. concession | Learning signals |
| 6 | **Confidence** | Not tracked | Required + calibration | Better reliability |

---

## Implementation Phases (Research Roadmap)

### Phase 1: Enhanced Critic Module
- Structured flaw reporting with location
- Geometry-specific attack patterns
- Counterexample generation
- Confidence scoring

### Phase 2: Integrated Generation-Criticism
- Outline generation step
- Insert critic after outline
- Generator revision before full proof

### Phase 3: Confidence Calibration
- Require confidence statements
- Test claims explicitly
- Penalty/reward system

### Phase 4: Curriculum Learning
- Geometry-specific progression
- Track attack effectiveness
- Adapt difficulty

### Phase 5: Analytics & Feedback
- Success rate metrics by attack type
- Systematic weakness identification
- Prompt optimization feedback

---

## How to Use This Research

### For Understanding the Problem
1. Read **rlac_summary.txt** (executive overview)
2. Review problem example in **rlac_gap_analysis.md**
3. Look at current architecture in **rlac_architecture_comparison.md**

### For Implementation Planning
1. Read **rlac_gap_analysis.md** (detailed analysis)
2. Review implementation roadmap sections
3. Check **rlac_architecture_comparison.md** for architectural guidance
4. Use Phase 1-5 roadmap for sprint planning

### For Specific Technical Details
- Structured flaw reporting format: **rlac_gap_analysis.md**, Section 2
- Geometry-specific attacks: **rlac_gap_analysis.md**, Section 3
- Confidence calibration: **rlac_architecture_comparison.md**, Confidence Calibration section
- Multi-stage pipeline: **rlac_gap_analysis.md**, section on Multi-Stage Verification

---

## Key Technical Insights

### 1. Timing Matters More Than Quality
A good critic running during generation beats an excellent critic running after completion, because feedback can reshape the generation process while it's still flexible.

### 2. Specificity Enables Learning
Structured flaws with location and suggested fixes enable targeted improvements, while binary verdicts force trial-and-error.

### 3. Domain Expertise Improves Attacks
Geometry-specific attack patterns (theorem preconditions, configuration properties) are more effective than generic reasoning checks.

### 4. Confidence Is a Vulnerability
Overconfident claims that fail verification are worse than careful partial claims. Penalizing miscalibration improves solution quality.

### 5. Defense vs. Concession Signals Learning
Tracking whether generators defend against or concede to attacks provides insight into what they've learned.

---

## Related Codebase Files

### Existing RLAC Implementation (in /home/user/IMO25/code/)
- `adversarial_critic.py` - Current adversarial critic implementation
- `adversarial_prompts.py` - Current attack prompt templates
- `agent_rlac.py` - RLAC orchestration agent

### Agent Architecture
- `agent_gpt_oss.py` - GPT-OSS agent with asymmetric reasoning
- `agent_oai.py` - OpenAI agent
- `agent_xai.py` - XAI Grok agent

### Test Case for This Research
- Problem: `/home/user/IMO25/problems/imo02.txt` (Geometry problem - circles and tangent)
- Log: `/home/user/IMO25/agent_gpt_oss_2_mcts_low_bfs.log` (Shows the gap)
- MCTS tree: `/home/user/IMO25/agent_gpt_oss_2_mcts_low_bfs_mcts_tree.json`

---

## Research Status

**Current Phase:** Analysis and Design (COMPLETE)
- Problem identified and analyzed
- Proposed solutions developed
- Architecture designed
- Implementation roadmap defined

**Next Phase:** Phase 1 Enhancement Implementation
- Enhanced critic module with structured feedback
- Geometry-specific attack patterns
- Ready for development

---

## Contact & Questions

This is research documentation only. For implementation discussions or questions, refer to:
- CLAUDE.md (system architecture overview)
- Code comments in agent files
- Git commit history for context

---

## Citation (for research purposes)

**RLAC Enhancement Research: Bridging the Generator-Verifier Gap in Mathematical Reasoning**
- Analysis: IMO25 Problem 02 (Geometry - circles and tangency)
- Gap: 0% verification pass rate despite apparent solution quality
- Solution: RLAC with during-generation adversarial feedback
- Timeline: Research document created 2025-11-22

---

## Document Index

```
/home/user/IMO25/docs/
├── README.md (this file)
│   └── Overview and navigation guide
├── rlac_summary.txt
│   └── Executive summary (10-15 min read)
├── rlac_gap_analysis.md
│   └── Detailed technical analysis (30-45 min read)
└── rlac_architecture_comparison.md
    └── Architecture diagrams and examples (20-30 min read)
```

---

**Document Version:** 1.0  
**Created:** 2025-11-22  
**Status:** Research Analysis Complete, Ready for Implementation Planning
