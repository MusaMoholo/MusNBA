# D56 larger-chunk latency checks

Before any 2.5k/5k layout result: compare the retained ordinary game401910038, same private inputs and
independent-fit candidate, ten single-thread workers, with the already measured 1k layout (74.441s).
Different layouts have distinct explicit sampling identities. No accuracy outcome selects the layout.

Run each larger layout separately without another heavy job. Its complete 10k latency is the estimand.
Stop a latency attempt if it remains incomplete at90s: it then cannot beat the measured 1k completion
time. Record only the lower bound, source/seed plan and stopped status; retain attempt files. This saves
unnecessary compute on a slower single-game layout. It is not a model rejection, simulation retry or
qualification sample, and no partial game is published. Never use the deadline on accuracy/stress runs.

Use `analysis/world_chunk_benchmark.py --game 401910038 --jobs 10 --chunk-worlds <2500|5000>
--max-seconds 90 --output <fresh experiment.json>`, with OMP/BLAS/VECLIB/MKL/NUMEXPR set to1.
The parent isolates its child process group and stops only that attempt and its workers at the limit.

Repeat the complete 1k arm after the larger layouts to check current-machine timing. Report completion
times/lower bounds, rather than treating censored attempts as completed batches. A full accepted nightly
then measures whole-slate throughput and accounting. A single game does not establish a universal optimum;
retain the fixed layout/seed namespace in every forecast's execution metadata.
