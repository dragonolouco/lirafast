from __future__ import annotations
import statistics, time
from semantic_compiler import SemanticCompiler
from runtime_v05 import LiraFastRuntime

def rate(label, fn, n=100_000, repeats=5):
    times=[]
    for _ in range(repeats):
        t=time.perf_counter()
        for i in range(n): fn(i)
        times.append(time.perf_counter()-t)
    med=statistics.median(times)
    print(f'{label}: {med:.6f}s total | {n/med:,.0f}/s | {med/n*1e6:.3f} us/op')

def main():
    c=SemanticCompiler(); text='crie uma função python para somar dois números e testar'
    rate('semantic_compile',lambda _:c.compile(text),n=50_000)
    rt=LiraFastRuntime(); compiled=rt.compiler.compile(text)
    for _ in range(3):rt.promoter.observe_success(domain='code',structure_signature=compiled.signature,op_ids=[1,2,7])
    rate('method_fast_path',lambda _:rt.route('faça function python adicionar números; teste',domain='code'),n=50_000)
    rt.save_verified_result(text,domain='code',result='verified-result',confidence=.999,verified_runs=4)
    rate('exact_result_path',lambda _:rt.route(text,domain='code'),n=50_000)

if __name__=='__main__':main()
