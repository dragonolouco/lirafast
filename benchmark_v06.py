from __future__ import annotations
import statistics,time
from formula_compiler import FormulaCompiler

EXPR='((a+b)*c - d) / (e+1)'

def bench(label,fn,n=100_000,repeats=5):
    vals=[]
    for _ in range(repeats):
        t=time.perf_counter()
        for i in range(n):fn(i)
        vals.append(time.perf_counter()-t)
    m=statistics.median(vals)
    print(f'{label}: {m:.6f}s | {n/m:,.0f}/s | {m/n*1e6:.3f} us/op')

def main():
    argv={'a':2.0,'b':3.0,'c':4.0,'d':1.0,'e':2.0}
    p=FormulaCompiler(tuple(argv)).compile(EXPR).program
    bench('execute_compiled',lambda _:p.execute(argv),50_000)
    bench('compile_plus_execute',lambda _:FormulaCompiler(tuple(argv)).compile(EXPR).program.execute(argv),10_000)

if __name__=='__main__':main()
