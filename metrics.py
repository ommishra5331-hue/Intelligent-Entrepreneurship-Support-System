"""Performance formulas used in the report (Sections 7, 8, 9 and test cases TC-01 to TC-10).

Each function is tagged with the CA&PP unit it comes from.
"""


# [CA&PP | Unit 3 - Control Unit & Pipelining] Time without pipelining: n tasks x k stages.
def sequential_cycles(n, k=5):
    return n * k


# [CA&PP | Unit 3 - Pipelining] Time with pipelining: k + n - 1 (+ stall cycles).
def pipelined_cycles(n, k=5, stalls=0):
    return k + n - 1 + stalls


# [CA&PP | Unit 3 - Pipelining] Speedup S = T_sequential / T_pipelined.
def pipeline_speedup(n, k=5, stalls=0):
    return sequential_cycles(n, k) / pipelined_cycles(n, k, stalls)


# [CA&PP | Unit 4 - Memory Organization] Hit ratio h = hits / total accesses.
def hit_ratio(hits, misses):
    total = hits + misses
    return hits / total if total else 0.0


# [CA&PP | Unit 4 - Memory Organization] Average access time T = h*tc + (1-h)*tm.
def amat(h, tc, tm):
    return h * tc + (1 - h) * tm


# [CA&PP | Unit 4 - Parallel Processing] Speedup S = T1 / Tp and efficiency E = S / p.
def speedup(t1, tp):
    return t1 / tp


def efficiency(s, p):
    return s / p


# [CA&PP | Unit 4 - Parallel Processing] Amdahl's law: S = 1 / ((1-f) + f/p).
def amdahl(f, p):
    return 1 / ((1 - f) + f / p)
