from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from snx.ast import (
    AddressOperand,
    InstructionIR,
    IRProgram,
    LabelRefOperand,
    Opcode,
)

if TYPE_CHECKING:
    pass


class EdgeKind(Enum):
    FALLTHROUGH = auto()
    BRANCH_TAKEN = auto()
    BRANCH_NOT_TAKEN = auto()
    CALL = auto()
    RETURN = auto()
    UNCONDITIONAL = auto()


@dataclass(frozen=True, slots=True)
class CFGEdge:
    source: int
    target: int
    kind: EdgeKind


@dataclass(slots=True)
class BasicBlock:
    start_pc: int
    end_pc: int
    instructions: list[InstructionIR] = field(default_factory=list)
    successors: list[int] = field(default_factory=list)
    predecessors: list[int] = field(default_factory=list)
    is_entry: bool = False
    is_exit: bool = False
    labels: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CFG:
    blocks: dict[int, BasicBlock]
    edges: list[CFGEdge]
    entry_pc: int
    exit_pcs: set[int]
    labels: dict[str, int]
    reverse_labels: dict[int, list[str]]

    def get_block_at(self, pc: int) -> BasicBlock | None:
        for block in self.blocks.values():
            if block.start_pc <= pc <= block.end_pc:
                return block
        return None

    def get_successors(self, pc: int) -> list[int]:
        result = []
        for edge in self.edges:
            if edge.source == pc:
                result.append(edge.target)
        return result

    def get_predecessors(self, pc: int) -> list[int]:
        result = []
        for edge in self.edges:
            if edge.target == pc:
                result.append(edge.source)
        return result


def _is_terminator(opcode: Opcode) -> bool:
    return opcode in (Opcode.BZ, Opcode.BAL, Opcode.HLT)


def _is_branch(opcode: Opcode) -> bool:
    return opcode in (Opcode.BZ, Opcode.BAL)


def build_cfg(ir_program: IRProgram) -> CFG:
    instructions = ir_program.instructions
    labels = ir_program.labels
    
    if not instructions:
        return CFG(
            blocks={},
            edges=[],
            entry_pc=0,
            exit_pcs=set(),
            labels=labels,
            reverse_labels={},
        )

    reverse_labels: dict[int, list[str]] = {}
    for label_name, pc in labels.items():
        if pc not in reverse_labels:
            reverse_labels[pc] = []
        reverse_labels[pc].append(label_name)

    block_starts: set[int] = {0}
    
    for inst in instructions:
        pc = inst.pc
        opcode = inst.opcode
        
        if opcode == Opcode.BZ:
            label_op = inst.operands[1]
            if isinstance(label_op, LabelRefOperand):
                target_pc = labels.get(label_op.name)
                if target_pc is not None:
                    block_starts.add(target_pc)
            block_starts.add(pc + 1)
            
        elif opcode == Opcode.BAL:
            target_op = inst.operands[1]
            if isinstance(target_op, LabelRefOperand):
                target_pc = labels.get(target_op.name)
                if target_pc is not None:
                    block_starts.add(target_pc)
            block_starts.add(pc + 1)
            
        elif opcode == Opcode.HLT:
            if pc + 1 < len(instructions):
                block_starts.add(pc + 1)

    for pc in labels.values():
        if pc < len(instructions):
            block_starts.add(pc)

    sorted_starts = sorted(block_starts)
    
    blocks: dict[int, BasicBlock] = {}
    for i, start_pc in enumerate(sorted_starts):
        if start_pc >= len(instructions):
            continue
            
        if i + 1 < len(sorted_starts):
            end_pc = sorted_starts[i + 1] - 1
        else:
            end_pc = len(instructions) - 1
        
        block_instructions = [
            inst for inst in instructions
            if start_pc <= inst.pc <= end_pc
        ]
        
        block_labels = reverse_labels.get(start_pc, [])
        
        block = BasicBlock(
            start_pc=start_pc,
            end_pc=end_pc,
            instructions=block_instructions,
            labels=block_labels,
        )
        blocks[start_pc] = block

    edges: list[CFGEdge] = []
    exit_pcs: set[int] = set()
    
    for block in blocks.values():
        if not block.instructions:
            continue
            
        last_inst = block.instructions[-1]
        last_pc = last_inst.pc
        opcode = last_inst.opcode
        
        if opcode == Opcode.HLT:
            block.is_exit = True
            exit_pcs.add(last_pc)
            
        elif opcode == Opcode.BZ:
            label_op = last_inst.operands[1]
            if isinstance(label_op, LabelRefOperand):
                target_pc = labels.get(label_op.name)
                if target_pc is not None:
                    edges.append(CFGEdge(last_pc, target_pc, EdgeKind.BRANCH_TAKEN))
            
            fallthrough_pc = last_pc + 1
            if fallthrough_pc < len(instructions):
                edges.append(CFGEdge(last_pc, fallthrough_pc, EdgeKind.BRANCH_NOT_TAKEN))
                
        elif opcode == Opcode.BAL:
            target_op = last_inst.operands[1]
            
            if isinstance(target_op, LabelRefOperand):
                target_pc = labels.get(target_op.name)
                if target_pc is not None:
                    edges.append(CFGEdge(last_pc, target_pc, EdgeKind.CALL))
                fallthrough_pc = last_pc + 1
                if fallthrough_pc < len(instructions):
                    edges.append(CFGEdge(last_pc, fallthrough_pc, EdgeKind.FALLTHROUGH))
            elif isinstance(target_op, AddressOperand):
                edges.append(CFGEdge(last_pc, -1, EdgeKind.RETURN))
        else:
            fallthrough_pc = last_pc + 1
            if fallthrough_pc < len(instructions):
                edges.append(CFGEdge(last_pc, fallthrough_pc, EdgeKind.FALLTHROUGH))

    for edge in edges:
        if edge.target >= 0 and edge.target in blocks:
            blocks[edge.target].predecessors.append(edge.source)
        source_block = None
        for b in blocks.values():
            if b.start_pc <= edge.source <= b.end_pc:
                source_block = b
                break
        if source_block and edge.target >= 0:
            if edge.target not in source_block.successors:
                source_block.successors.append(edge.target)

    entry_pc = labels.get("main", 0)
    if entry_pc in blocks:
        blocks[entry_pc].is_entry = True

    return CFG(
        blocks=blocks,
        edges=edges,
        entry_pc=entry_pc,
        exit_pcs=exit_pcs,
        labels=labels,
        reverse_labels=reverse_labels,
    )


def find_reachable_pcs(cfg: CFG, start_pc: int) -> set[int]:
    reachable: set[int] = set()
    worklist = [start_pc]
    
    while worklist:
        pc = worklist.pop()
        if pc in reachable or pc < 0:
            continue
        reachable.add(pc)
        
        block = cfg.get_block_at(pc)
        if block:
            for inst_pc in range(block.start_pc, block.end_pc + 1):
                reachable.add(inst_pc)
            
            for succ_pc in block.successors:
                if succ_pc not in reachable:
                    worklist.append(succ_pc)
    
    return reachable


def find_strongly_connected_components(cfg: CFG) -> list[set[int]]:
    all_pcs = set()
    for block in cfg.blocks.values():
        for inst in block.instructions:
            all_pcs.add(inst.pc)
    
    index_counter = [0]
    stack: list[int] = []
    lowlinks: dict[int, int] = {}
    index: dict[int, int] = {}
    on_stack: set[int] = set()
    sccs: list[set[int]] = []
    
    def get_successors(pc: int) -> list[int]:
        result = []
        for edge in cfg.edges:
            if edge.source == pc and edge.target >= 0:
                result.append(edge.target)
        return result
    
    def strongconnect(v: int) -> None:
        index[v] = index_counter[0]
        lowlinks[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        
        for w in get_successors(v):
            if w not in index:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], index[w])
        
        if lowlinks[v] == index[v]:
            scc: set[int] = set()
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.add(w)
                if w == v:
                    break
            sccs.append(scc)
    
    for pc in all_pcs:
        if pc not in index:
            strongconnect(pc)
    
    return sccs


def find_infinite_loop_sccs(cfg: CFG) -> list[set[int]]:
    sccs = find_strongly_connected_components(cfg)
    infinite_sccs: list[set[int]] = []
    
    for scc in sccs:
        if len(scc) <= 1:
            pc = next(iter(scc))
            has_self_loop = False
            for edge in cfg.edges:
                if edge.source == pc and edge.target == pc:
                    has_self_loop = True
                    break
            if not has_self_loop:
                continue
        
        has_exit = False
        has_external_edge = False
        
        for pc in scc:
            if pc in cfg.exit_pcs:
                has_exit = True
                break
            
            for edge in cfg.edges:
                if edge.source == pc and edge.target not in scc and edge.target >= 0:
                    has_external_edge = True
                    break
            
            if has_external_edge:
                break
        
        if not has_exit and not has_external_edge:
            infinite_sccs.append(scc)
    
    return infinite_sccs
