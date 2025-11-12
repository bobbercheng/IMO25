#!/usr/bin/env python3

"""
MIT License

Copyright (c) 2025 Lin Yang, Yichen Huang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import subprocess
import os
import sys
import argparse
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import signal
import threading
import json
import re

# Globals used within worker processes to forward termination to child agent
current_child_process = None
_signal_handlers_installed = False

def _install_worker_signal_handlers():
    """Install SIGTERM/SIGINT handlers in worker to terminate spawned agent."""
    global _signal_handlers_installed
    if _signal_handlers_installed:
        return

    def _forward_signal(signum, frame):
        # Kill the entire child process group if available, then exit fast
        try:
            if current_child_process is not None and current_child_process.poll() is None:
                try:
                    pgid = os.getpgid(current_child_process.pid)
                    os.killpg(pgid, signum)
                except Exception:
                    try:
                        current_child_process.terminate()
                    except Exception:
                        pass
        finally:
            # Avoid executor cleanup delays inside workers
            os._exit(0)

    signal.signal(signal.SIGTERM, _forward_signal)
    signal.signal(signal.SIGINT, _forward_signal)
    _signal_handlers_installed = True

def run_agent(agent_id, problem_file, log_dir, timeout=None, other_prompts=[], agent_file='agent.py',
               benchmark=None, level=None, benchmark_index=None):
    """
    Run a single agent instance with the specified parameters.

    Args:
        agent_id: Unique identifier for this agent instance
        problem_file: Path to the problem statement file (optional if using benchmark)
        log_dir: Directory to store log files
        timeout: Timeout in seconds (None for no timeout)
        other_prompts: List of additional prompts to use
        agent_file: Path to the agent file to execute (default: agent.py)
        benchmark: Benchmark to use (gradingbench or proofbench, optional)
        level: Level to filter by (Basic, Advanced, optional)
        benchmark_index: Index of problem to load from benchmark (optional)

    Returns:
        tuple: (agent_id, return_code, stdout, stderr, solution_found)
    """
    log_file = os.path.join(log_dir, f"agent_{agent_id:02d}.log")

    # Build command based on whether we're using a problem file or benchmark
    if benchmark:
        cmd = [
            sys.executable, agent_file,
            "--benchmark", benchmark,
            "--log", log_file,
            "--other_prompts", f'\"{",".join(other_prompts)}\"'
        ]
        if level:
            cmd.extend(["--level", level])
        if benchmark_index is not None:
            cmd.extend(["--benchmark-index", str(benchmark_index)])
    else:
        cmd = [
            sys.executable, agent_file,
            problem_file,
            "--log", log_file,
            "--other_prompts", f'\"{",".join(other_prompts)}\"'
        ]
    
    try:
        # Ensure worker can forward signals to child agent process
        _install_worker_signal_handlers()

        # Launch agent as its own process group so we can kill the whole tree
        global current_child_process
        current_child_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            start_new_session=True,
        )

        try:
            if timeout:
                stdout_text, stderr_text = current_child_process.communicate(timeout=timeout)
            else:
                stdout_text, stderr_text = current_child_process.communicate()
        except subprocess.TimeoutExpired:
            # Kill process group on timeout
            try:
                os.killpg(os.getpgid(current_child_process.pid), signal.SIGKILL)
            except Exception:
                try:
                    current_child_process.kill()
                except Exception:
                    pass
            return (agent_id, -1, "", f"Agent {agent_id} timed out after {timeout} seconds", False)
        finally:
            return_code = current_child_process.returncode
            current_child_process = None

        # Check if a solution was found by looking for the success message
        solution_found = False
        if return_code == 0:
            if "Found a correct solution in run" in stdout_text:
                solution_found = True
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                    if "Found a correct solution in run" in log_content:
                        solution_found = True
            except Exception:
                pass

        return (agent_id, return_code, stdout_text, stderr_text, solution_found)
    except Exception as e:
        return (agent_id, -1, "", f"Agent {agent_id} failed with error: {str(e)}", False)

def print_status(agent_id, status, stdout="", stderr=""):
    """Print status information for an agent."""
    print(f"[Agent {agent_id:02d}] {status}")
    if stdout.strip():
        print(f"[Agent {agent_id:02d}] STDOUT: {stdout.strip()}")
    if stderr.strip():
        print(f"[Agent {agent_id:02d}] STDERR: {stderr.strip()}")

def main():
    parser = argparse.ArgumentParser(description='Run multiple IMO agent instances in parallel')
    parser.add_argument('problem_file', nargs='?', default=None,
                       help='Path to the problem statement file (optional if using --benchmark)')
    parser.add_argument('--num-agents', '-n', type=int, default=10,
                       help='Number of parallel agents to run (default: 10)')
    parser.add_argument('--log-dir', '-d', default='logs',
                       help='Directory to store log files (default: logs)')
    parser.add_argument('--timeout', '-t', type=int, default=None,
                       help='Timeout in seconds for each agent (default: no timeout)')
    parser.add_argument('--max-workers', '-w', type=int, default=None,
                       help='Maximum number of worker processes (default: number of agents)')
    parser.add_argument('--other_prompts', '-o', type=str, help='Other prompts (optional)')
    parser.add_argument('--agent-file', '-a', type=str, default='agent.py',
                       help='Path to the agent file to run (default: agent.py)')
    parser.add_argument('--exit-immediately', '-e', action='store_true',
                       help='Exit immediately when solution is found (default: graceful shutdown)')
    parser.add_argument('--benchmark', '-b', type=str, choices=['gradingbench', 'proofbench'],
                       help='Load problems from benchmark (gradingbench or proofbench)')
    parser.add_argument('--level', type=str,
                       help='Filter benchmark by level (Basic, Advanced). Case-insensitive.')
    parser.add_argument('--benchmark-start-index', type=int, default=0,
                       help='Starting index for benchmark problems (default: 0)')


    args = parser.parse_args()

    # Validate that either problem_file or benchmark is specified
    if not args.problem_file and not args.benchmark:
        print("Error: Either problem_file or --benchmark must be specified")
        parser.print_help()
        sys.exit(1)
    
    # Create log directory if it doesn't exist
    os.makedirs(args.log_dir, exist_ok=True)
    
    print(f"Starting {args.num_agents} parallel agents...")
    if args.benchmark:
        print(f"Benchmark: {args.benchmark}")
        if args.level:
            print(f"Level filter: {args.level}")
        print(f"Starting from benchmark index: {args.benchmark_start_index}")
    else:
        print(f"Problem file: {args.problem_file}")
    print(f"Agent file: {args.agent_file}")
    print(f"Log directory: {args.log_dir}")
    print(f"Exit behavior: {'Immediate exit' if args.exit_immediately else 'Run all agents to completion'} when solution found")
    if args.timeout:
        print(f"Timeout per agent: {args.timeout} seconds")
    print(f"Max workers: {args.max_workers or args.num_agents}")
    if not args.exit_immediately:
        print("Note: All agents will run to completion regardless of solution found")
    print("-" * 50)
    
    # Track results
    completed_agents = []
    successful_agents = []
    failed_agents = []
    solution_found = False
    solution_agent_id = None

    other_prompts = []
    if args.other_prompts:
        other_prompts = args.other_prompts.split(',')
    
    start_time = time.time()
    
    try:
        with ProcessPoolExecutor(max_workers=args.max_workers or args.num_agents) as executor:
            # Submit all agent tasks
            if args.benchmark:
                # When using benchmark, each agent gets a different benchmark index
                future_to_agent = {
                    executor.submit(
                        run_agent, i, args.problem_file, args.log_dir, args.timeout, other_prompts, args.agent_file,
                        args.benchmark, args.level, args.benchmark_start_index + i
                    ): i
                    for i in range(args.num_agents)
                }
            else:
                # When using a problem file, all agents work on the same problem
                future_to_agent = {
                    executor.submit(run_agent, i, args.problem_file, args.log_dir, args.timeout, other_prompts, args.agent_file): i
                    for i in range(args.num_agents)
                }
            
            # Process completed agents
            for future in as_completed(future_to_agent):
                agent_id, return_code, stdout, stderr, found_solution = future.result()
                completed_agents.append(agent_id)
                
                if found_solution:
                    solution_found = True
                    solution_agent_id = agent_id
                    status = "FOUND CORRECT SOLUTION!"
                    successful_agents.append(agent_id)
                    print(f"\n🎉 SOLUTION FOUND by Agent {agent_id:02d}! 🎉")
                    print(f"[Agent {agent_id:02d}] {status}")
                    print_status(agent_id, status, stdout, stderr)
                    
                    if args.exit_immediately:
                        # Exit immediately when solution is found
                        print(f"\nExiting immediately as requested...")
                        # Cancel pending tasks and stop scheduling new ones
                        try:
                            executor.shutdown(wait=False, cancel_futures=True)
                        except Exception:
                            pass
                        # Print a concise early-exit summary with the winning agent
                        try:
                            elapsed = time.time() - start_time
                            print("\n" + "=" * 50)
                            print("EARLY EXIT SUMMARY")
                            print("=" * 50)
                            print(f"Correct solution found by Agent {agent_id:02d}")
                            print(f"Log file: {os.path.join(args.log_dir, f'agent_{agent_id:02d}.log')}")
                            print(f"Elapsed time: {elapsed:.2f} seconds")
                        except Exception:
                            pass
                        # Terminate all worker processes so they forward termination to their child agents
                        try:
                            worker_processes = list(getattr(executor, "_processes", {}).values())
                            for p in worker_processes:
                                try:
                                    p.terminate()
                                except Exception:
                                    try:
                                        os.kill(p.pid, signal.SIGTERM)
                                    except Exception:
                                        pass
                            # Brief grace period, then force kill remaining
                            time.sleep(0.5)
                            for p in worker_processes:
                                try:
                                    if hasattr(p, "is_alive") and p.is_alive():
                                        p.kill()
                                except Exception:
                                    try:
                                        os.kill(p.pid, signal.SIGKILL)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        # Exit the main process immediately without waiting for context cleanup
                        os._exit(0)
                    # Otherwise, continue running all agents to completion
                elif return_code == 0:
                    status = "COMPLETED SUCCESSFULLY (no solution found)"
                    successful_agents.append(agent_id)
                else:
                    status = f"FAILED (return code: {return_code})"
                    failed_agents.append(agent_id)
                
                print_status(agent_id, status, stdout, stderr)
                print(f"Progress: {len(completed_agents)}/{args.num_agents} agents completed")
                print("-" * 30)
    
    except KeyboardInterrupt:
        print("\nReceived interrupt signal. Shutting down gracefully...")
        # The ProcessPoolExecutor will handle cleanup automatically
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print summary
    print("\n" + "=" * 50)
    print("FINAL SUMMARY")
    print("=" * 50)
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Total agents: {args.num_agents}")
    print(f"Successful agents: {len(successful_agents)}")
    print(f"Failed agents: {len(failed_agents)}")
    print(f"Success rate: {len(successful_agents)/args.num_agents*100:.1f}%")
    
    if solution_found:
        print(f"\n🎉 SOLUTION FOUND by Agent {solution_agent_id:02d}! 🎉")
        print(f"Log file with solution: {os.path.join(args.log_dir, f'agent_{solution_agent_id:02d}.log')}")
        
        # Try to extract and display the solution
        solution_log_file = os.path.join(args.log_dir, f"agent_{solution_agent_id:02d}.log")
        try:
            with open(solution_log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
                # Look for the solution in the log
                if "Found a correct solution in run" in log_content:
                    # Extract the solution JSON
                    solution_match = re.search(r'Found a correct solution in run \d+\.\s*\n(.*?)(?=\n\n|\n>>>>>>>|\Z)', 
                                            log_content, re.DOTALL)
                    if solution_match:
                        solution_text = solution_match.group(1).strip()
                        print(f"\nSOLUTION FOUND:")
                        print("=" * 50)
                        print(solution_text)
                        print("=" * 50)
        except Exception as e:
            print(f"Could not extract solution from log file: {e}")
    
    if successful_agents:
        print(f"\nSuccessful agent IDs: {sorted(successful_agents)}")
    
    if failed_agents:
        print(f"Failed agent IDs: {sorted(failed_agents)}")
    
    print(f"\nLog files are available in: {os.path.abspath(args.log_dir)}")
    
    # List log files
    log_files = [f for f in os.listdir(args.log_dir) if f.endswith('.log')]
    if log_files:
        print(f"\nGenerated log files:")
        for log_file in sorted(log_files):
            file_path = os.path.join(args.log_dir, log_file)
            file_size = os.path.getsize(file_path)
            print(f"  {log_file} ({file_size} bytes)")
    
    return 0 if solution_found else 1

if __name__ == "__main__":
    sys.exit(main()) 