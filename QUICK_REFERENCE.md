# Quick Reference: MCTS + Translation Layer

## 🚀 Quick Commands

### Standard BFS (Proven Baseline)
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning low \
  --num-initial-attempts 5 \
  --log bfs.log
```
**Expected**: 60-80% success, $15-25/problem

---

### Translation Layer (Asymmetric Fix)
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --use-translation \
  --num-initial-attempts 3 \
  --log translation.log
```
**Expected**: 60-75% success, $12-18/problem

---

### MCTS Exploration (Recommended)
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning medium \
  --verification-reasoning medium \
  --use-mcts \
  --mcts-simulations 8 \
  --log mcts.log
```
**Expected**: 65-85% success, $20-30/problem

---

### MCTS + Translation (Maximum Power)
```bash
python code/agent_gpt_oss.py problems/imo01.txt \
  --solution-reasoning low \
  --verification-reasoning high \
  --use-mcts \
  --use-translation \
  --mcts-simulations 10 \
  --log mcts_translation.log
```
**Expected**: 70-90% success, $25-35/problem

---

## 📊 Configuration Matrix

| Feature | Flag | When to Use |
|---------|------|-------------|
| BFS | `--num-initial-attempts N` | Always (baseline) |
| MCTS | `--use-mcts` | Hard problems |
| Translation | `--use-translation` | Asymmetric reasoning |
| Low Reasoning | `--solution-reasoning low` | Speed, cost |
| Medium Reasoning | `--solution-reasoning medium` | Balance |
| High Reasoning | `--solution-reasoning high` | Rigor (caution: truncation) |

---

## 🔍 Log Markers

| Marker | Meaning |
|--------|---------|
| `[MCTS]` | MCTS exploration activity |
| `[TRANSLATION]` | Translation layer activity |
| `>>>>>>> BFS:` | Standard BFS activity |
| `Found a correct solution` | SUCCESS! |

---

## ⚙️ Key Parameters

### MCTS
- `--mcts-simulations`: 5-15 (more = better but slower)
- `--mcts-exploration`: 1.0 (exploit) to 2.5 (explore)

### Translation
- `--use-translation`: Enables translation layer
- Auto-activates when: low gen + high/medium ver

---

## 🎯 Decision Tree

```
Problem Difficulty?
├─ Easy → BFS (low/low/low, 3 attempts)
├─ Medium → MCTS (medium/medium/medium, 8 sims)
└─ Hard → MCTS + Translation (low/high, 10 sims)

Budget?
├─ <$20 → BFS or Translation
├─ $20-30 → MCTS
└─ $30+ → MCTS + Translation

Need proven approach?
└─ Yes → BFS (low/low/low, 5 attempts) ✅ 100% in test
```

---

## 📈 Success Rates (Expected)

| Configuration | Success | Cost | Speed |
|--------------|---------|------|-------|
| BFS Low | 60-80% | $15-25 | ⚡⚡⚡ |
| Asymmetric + Translation | 60-75% | $12-18 | ⚡⚡ |
| MCTS Medium | 65-85% | $20-30 | ⚡⚡ |
| MCTS + Translation | 70-90% | $25-35 | ⚡ |

---

## 🧪 Test Suite

Run all tests:
```bash
./test_mcts_translation.sh
```

Results in: `test_logs_mcts_translation/`

---

## 📚 Full Documentation

- **MCTS_TRANSLATION_GUIDE.md**: Complete guide
- **GPT-OSS_Agent.md**: Technical analysis
- **CLAUDE.md**: Architecture overview
- **code/mcts_bfs.py**: MCTS source code
- **code/agent_gpt_oss.py**: Main agent

---

## 🐛 Troubleshooting

**Translation not working?**
```bash
# Check log for:
>>>>>>> Translation layer ENABLED
>>>>>>> Asymmetric reasoning detected
```

**MCTS import error?**
```bash
# Verify file exists:
ls -la code/mcts_bfs.py
```

**High costs?**
```bash
# Use lower reasoning:
--solution-reasoning low \
--verification-reasoning medium
```

---

## 💡 Pro Tips

1. **Start with BFS** (proven baseline)
2. **Add translation** if using asymmetric
3. **Use MCTS** for hard problems
4. **Combine all** for maximum success rate
5. **Check logs** for [MCTS] and [TRANSLATION] markers

---

## Example Output

### MCTS
```
[MCTS] Simulation 3/8
[MCTS] Selected 'Mathematical induction' (UCB1=2.45)
[MCTS] Score: 75.5
[MCTS] New best solution!
```

### Translation
```
[TRANSLATION] Original: 2847 chars
[TRANSLATION] Simplified: 1123 chars (60% reduction)
[TRANSLATION] Quality: GOOD ✓
```

---

**Quick Start**: `python code/agent_gpt_oss.py problems/imo01.txt --use-mcts --log test.log`
