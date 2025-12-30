#!/bin/bash
# Analyze N=20 validation results

echo "Run,Success,Validator,Iterations,Final_Answer,Critical_Errors"

for log in bfs_validation_n20/bfs_run*_20251222_162739.log; do
  run=$(basename "$log" | sed 's/bfs_run\([0-9]*\)_.*/\1/')

  # Check for success
  if grep -q "verification good" "$log" 2>/dev/null; then
    success=1
  else
    success=0
  fi

  # Count validator invocations
  validator=$(grep -c "ANSWER VALIDATION" "$log" 2>/dev/null || echo 0)

  # Extract iterations
  iterations=$(grep "Iteration [0-9]" "$log" | tail -1 | sed -n 's/.*Iteration \([0-9]*\).*/\1/p' || echo "0")

  # Extract final answer from last boxed answer
  final_answer=$(grep -o '\\boxed{[^}]*}' "$log" | tail -1 | sed 's/\\boxed{\(.*\)}/\1/' || echo "NONE")

  # Count Critical Errors
  critical_errors=$(grep -c "Critical Error" "$log" 2>/dev/null || echo 0)

  echo "$run,$success,$validator,$iterations,$final_answer,$critical_errors"
done
