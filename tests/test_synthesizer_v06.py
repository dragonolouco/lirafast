from auto_learning import discover_and_learn
from program_learning import Example
from program_store import ProgramStore
from program_synthesizer import SynthesisExample, synthesize_formula
from structural_memory import StructuralMemory

def test_synthesizes_addition_from_examples():
    ex=[SynthesisExample({'a':1,'b':2},3),SynthesisExample({'a':5,'b':8},13),SynthesisExample({'a':-2,'b':9},7)]
    r=synthesize_formula(inputs=('a','b'),examples=ex,max_depth=1)
    assert r is not None
    assert r.program.execute({'a':123,'b':456})==579

def test_synthesizes_small_composed_formula():
    ex=[SynthesisExample({'a':1,'b':2},4),SynthesisExample({'a':3,'b':4},10),SynthesisExample({'a':-2,'b':5},1)]
    # target = a*2 + b
    r=synthesize_formula(inputs=('a','b'),examples=ex,max_depth=2)
    assert r is not None
    assert r.program.execute({'a':10,'b':7})==27

def test_behavior_dedup_keeps_search_bounded():
    ex=[SynthesisExample({'a':1},2),SynthesisExample({'a':2},3)]
    r=synthesize_formula(inputs=('a',),examples=ex,max_depth=2,max_unique=1000)
    assert r is not None
    assert r.unique_behaviors<=1000

def test_auto_discovery_promotes_runnable_method():
    mem=StructuralMemory(); store=ProgramStore()
    ex=[Example({'x':2},5),Example({'x':5},11),Example({'x':-1},-1)] # 2*x+1
    r=discover_and_learn(memory=mem,programs=store,method_id='auto-linear',domain='math',structure_signature='linear',inputs=('x',),examples=ex,max_depth=2)
    assert r is not None
    assert mem.best_method('linear','math') is not None
    assert store.get('auto-linear').execute({'x':10})==21
