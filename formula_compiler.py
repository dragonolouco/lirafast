from __future__ import annotations
"""Safe expression -> NumericProgram compiler.

Only a deliberately small mathematical AST is accepted. No attributes, imports,
subscripting, arbitrary calls, comprehensions or Python eval are used.
"""
import ast
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple
from numeric_vm import Instruction, NumericProgram, Op

_BIN={ast.Add:Op.ADD,ast.Sub:Op.SUB,ast.Mult:Op.MUL,ast.Div:Op.DIV,ast.Mod:Op.MOD,ast.Pow:Op.POW}
_CMP={ast.Eq:Op.EQ,ast.NotEq:Op.NE,ast.Lt:Op.LT,ast.LtE:Op.LE,ast.Gt:Op.GT,ast.GtE:Op.GE}

@dataclass(frozen=True)
class CompiledFormula:
    expression:str
    program:NumericProgram

class FormulaCompiler:
    def __init__(self,inputs:Sequence[str]|None=None)->None:
        self.explicit_inputs=tuple(inputs) if inputs is not None else None
        self._names:List[str]=[]
        self._name_index:Dict[str,int]={}
        self._consts:List[float]=[]
        self._const_index:Dict[float,int]={}
        self._code:List[Instruction]=[]

    def _input(self,name:str)->int:
        if self.explicit_inputs is not None:
            if name not in self.explicit_inputs: raise ValueError(f"unknown input {name!r}")
            return self.explicit_inputs.index(name)
        if name not in self._name_index:
            self._name_index[name]=len(self._names); self._names.append(name)
        return self._name_index[name]

    def _const(self,value:float)->int:
        v=float(value)
        if v not in self._const_index:
            self._const_index[v]=len(self._consts); self._consts.append(v)
        return self._const_index[v]

    def compile(self,expression:str)->CompiledFormula:
        self._names=[]; self._name_index={}; self._consts=[]; self._const_index={}; self._code=[]
        tree=ast.parse(expression,mode="eval")
        self._emit(tree.body); self._code.append(Instruction(Op.RETURN))
        inputs=self.explicit_inputs if self.explicit_inputs is not None else tuple(self._names)
        p=NumericProgram(tuple(inputs),tuple(self._consts),tuple(self._code)); p.validate()
        return CompiledFormula(expression,p)

    def _emit(self,node:ast.AST)->None:
        if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)) and not isinstance(node.value,bool):
            self._code.append(Instruction(Op.LOAD_CONST,self._const(float(node.value)))); return
        if isinstance(node,ast.Name):
            self._code.append(Instruction(Op.LOAD_INPUT,self._input(node.id))); return
        if isinstance(node,ast.BinOp) and type(node.op) in _BIN:
            self._emit(node.left); self._emit(node.right); self._code.append(Instruction(_BIN[type(node.op)])); return
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
            self._emit(node.operand)
            if isinstance(node.op,ast.USub): self._code.append(Instruction(Op.NEG))
            return
        if isinstance(node,ast.Compare) and len(node.ops)==1 and len(node.comparators)==1 and type(node.ops[0]) in _CMP:
            self._emit(node.left); self._emit(node.comparators[0]); self._code.append(Instruction(_CMP[type(node.ops[0])]))
            return
        if isinstance(node,ast.IfExp):
            self._emit(node.test); self._emit(node.body); self._emit(node.orelse); self._code.append(Instruction(Op.SELECT)); return
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            name=node.func.id
            if name=="abs" and len(node.args)==1:
                self._emit(node.args[0]); self._code.append(Instruction(Op.ABS)); return
            if name in {"min","max"} and len(node.args)==2:
                self._emit(node.args[0]); self._emit(node.args[1]); self._code.append(Instruction(Op.MIN if name=="min" else Op.MAX)); return
        raise ValueError(f"unsupported formula node: {ast.dump(node,include_attributes=False)}")
