#!/bin/bash
for log in bfs_validation_n20/bfs_run*_20251222_162739.log; do
  run=$(basename "$log" | sed 's/bfs_run\([0-9]*\)_.*/\1/')
  if grep -q "No solution found" "$log"; then
    status="FAILED"
  else
    status="UNKNOWN"
  fi
  echo "Run $run: $status"
done
