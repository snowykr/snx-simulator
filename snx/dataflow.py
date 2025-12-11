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
    RegisterOperand,
)
from snx.cfg import CFG, build_cfg
from snx.constants import DEFAULT_REG_COUNT
from snx.word import normalize_imm8

if TYPE_CHECKING:
    pass


class ValueState(Enum):
    UNINIT = auto()
    DATA = auto()
    RETURN_ADDR = auto()
    UNKNOWN = auto()

    def merge_with(self, other: ValueState) -> ValueState:
        if self == other:
            return self
        if self == ValueState.UNINIT or other == ValueState.UNINIT:
            return ValueState.UNKNOWN
        if self == ValueState.UNKNOWN or other == ValueState.UNKNOWN:
            return ValueState.UNKNOWN
        return ValueState.UNKNOWN


@dataclass(slots=True)
class AbstractState:
    registers: dict[int, ValueState] = field(default_factory=dict)
    stack_slots: dict[int, ValueState] = field(default_factory=dict)
    sp_offset: int = 0
    
    def copy(self) -> AbstractState:
        return AbstractState(
            registers=dict(self.registers),
            stack_slots=dict(self.stack_slots),
            sp_offset=self.sp_offset,
        )
    
    def merge_with(self, other: AbstractState) -> AbstractState:
        result = AbstractState()
        
        all_regs = set(self.registers.keys()) | set(other.registers.keys())
        for reg in all_regs:
            self_state = self.registers.get(reg, ValueState.UNINIT)
            other_state = other.registers.get(reg, ValueState.UNINIT)
            result.registers[reg] = self_state.merge_with(other_state)
        
        all_slots = set(self.stack_slots.keys()) | set(other.stack_slots.keys())
        for slot in all_slots:
            self_state = self.stack_slots.get(slot, ValueState.UNINIT)
            other_state = other.stack_slots.get(slot, ValueState.UNINIT)
            result.stack_slots[slot] = self_state.merge_with(other_state)
        
        result.sp_offset = max(self.sp_offset, other.sp_offset)
        
        return result
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractState):
            return False
        return (self.registers == other.registers and 
                self.stack_slots == other.stack_slots and
                self.sp_offset == other.sp_offset)


@dataclass(frozen=True, slots=True)
class DataflowIssue:
    pc: int
    code: str
    message: str
    severity: str
    instruction_text: str


@dataclass(slots=True)
class DataflowResult:
    issues: list[DataflowIssue]
    states_at_pc: dict[int, AbstractState]
    unreachable_pcs: set[int]


class DataflowAnalyzer:
    def __init__(
        self,
        ir_program: IRProgram,
        cfg: CFG,
        *,
        reg_count: int = DEFAULT_REG_COUNT,
    ) -> None:
        self._ir_program = ir_program
        self._cfg = cfg
        self._reg_count = reg_count
        self._issues: list[DataflowIssue] = []
        self._states: dict[int, AbstractState] = {}
        self._inst_by_pc: dict[int, InstructionIR] = {
            inst.pc: inst for inst in ir_program.instructions
        }
        
    def analyze(self) -> DataflowResult:
        if not self._ir_program.instructions:
            return DataflowResult(
                issues=[],
                states_at_pc={},
                unreachable_pcs=set(),
            )
        
        entry_state = AbstractState()
        entry_state.registers[0] = ValueState.DATA
        for i in range(1, self._reg_count):
            entry_state.registers[i] = ValueState.UNINIT
        
        entry_pc = self._cfg.entry_pc
        self._states[entry_pc] = entry_state
        
        worklist = [entry_pc]
        visited_count: dict[int, int] = {}
        max_iterations = len(self._ir_program.instructions) * 10
        
        while worklist and max_iterations > 0:
            max_iterations -= 1
            pc = worklist.pop(0)
            
            if pc not in self._inst_by_pc:
                continue
            
            visited_count[pc] = visited_count.get(pc, 0) + 1
            if visited_count[pc] > 20:
                continue
            
            inst = self._inst_by_pc[pc]
            in_state = self._states.get(pc, AbstractState())
            
            out_state, successors = self._transfer(inst, in_state)
            
            for succ_pc in successors:
                if succ_pc < 0:
                    continue
                    
                if succ_pc in self._states:
                    merged = self._states[succ_pc].merge_with(out_state)
                    if merged != self._states[succ_pc]:
                        self._states[succ_pc] = merged
                        if succ_pc not in worklist:
                            worklist.append(succ_pc)
                else:
                    self._states[succ_pc] = out_state.copy()
                    if succ_pc not in worklist:
                        worklist.append(succ_pc)
        
        all_pcs = set(self._inst_by_pc.keys())
        reachable_pcs = set(self._states.keys())
        unreachable_pcs = all_pcs - reachable_pcs
        
        return DataflowResult(
            issues=self._issues,
            states_at_pc=self._states,
            unreachable_pcs=unreachable_pcs,
        )
    
    def _transfer(
        self,
        inst: InstructionIR,
        in_state: AbstractState,
    ) -> tuple[AbstractState, list[int]]:
        out_state = in_state.copy()
        successors: list[int] = []
        pc = inst.pc
        opcode = inst.opcode
        operands = inst.operands
        
        if opcode == Opcode.LDA:
            dest = operands[0]
            addr_op = operands[1]
            if isinstance(dest, RegisterOperand):
                out_state.registers[dest.index] = ValueState.DATA
                if dest.index == 3 and isinstance(addr_op, AddressOperand):
                    if addr_op.base.index == 3:
                        out_state.sp_offset += normalize_imm8(addr_op.offset)
            successors.append(pc + 1)
            
        elif opcode == Opcode.LD:
            dest = operands[0]
            addr_op = operands[1]
            if isinstance(dest, RegisterOperand) and isinstance(addr_op, AddressOperand):
                slot_key = self._get_stack_slot_key(addr_op, in_state)
                if slot_key is not None:
                    slot_state = in_state.stack_slots.get(slot_key, ValueState.UNINIT)
                    if slot_state == ValueState.UNINIT:
                        self._issues.append(DataflowIssue(
                            pc=pc,
                            code="D001",
                            message=f"Reading from uninitialized memory at {addr_op.text}",
                            severity="error",
                            instruction_text=inst.text,
                        ))
                        out_state.registers[dest.index] = ValueState.UNKNOWN
                    elif slot_state == ValueState.UNKNOWN:
                        self._issues.append(DataflowIssue(
                            pc=pc,
                            code="D002",
                            message=f"Reading from potentially uninitialized memory at {addr_op.text}",
                            severity="warning",
                            instruction_text=inst.text,
                        ))
                        out_state.registers[dest.index] = ValueState.UNKNOWN
                    else:
                        out_state.registers[dest.index] = slot_state
                else:
                    out_state.registers[dest.index] = ValueState.UNKNOWN
            successors.append(pc + 1)
            
        elif opcode == Opcode.ST:
            src = operands[0]
            addr_op = operands[1]
            if isinstance(src, RegisterOperand) and isinstance(addr_op, AddressOperand):
                slot_key = self._get_stack_slot_key(addr_op, in_state)
                if slot_key is not None:
                    src_state = in_state.registers.get(src.index, ValueState.UNINIT)
                    out_state.stack_slots[slot_key] = src_state
            successors.append(pc + 1)
            
        elif opcode in (Opcode.ADD, Opcode.AND, Opcode.SUB, Opcode.SLT):
            dest = operands[0]
            if isinstance(dest, RegisterOperand):
                out_state.registers[dest.index] = ValueState.DATA
            successors.append(pc + 1)
            
        elif opcode in (Opcode.NOT, Opcode.SR):
            dest = operands[0]
            if isinstance(dest, RegisterOperand):
                out_state.registers[dest.index] = ValueState.DATA
            successors.append(pc + 1)
            
        elif opcode == Opcode.IN:
            dest = operands[0]
            if isinstance(dest, RegisterOperand):
                out_state.registers[dest.index] = ValueState.DATA
            successors.append(pc + 1)
            
        elif opcode == Opcode.OUT:
            successors.append(pc + 1)
            
        elif opcode == Opcode.BZ:
            label_op = operands[1]
            if isinstance(label_op, LabelRefOperand):
                target_pc = self._cfg.labels.get(label_op.name)
                if target_pc is not None:
                    successors.append(target_pc)
            successors.append(pc + 1)
            
        elif opcode == Opcode.BAL:
            link_reg = operands[0]
            target_op = operands[1]
            
            if isinstance(link_reg, RegisterOperand):
                out_state.registers[link_reg.index] = ValueState.RETURN_ADDR
            
            if isinstance(target_op, LabelRefOperand):
                target_pc = self._cfg.labels.get(target_op.name)
                if target_pc is not None:
                    successors.append(target_pc)
                    successors.append(pc + 1)
                    
            elif isinstance(target_op, AddressOperand):
                base_reg = target_op.base
                if isinstance(base_reg, RegisterOperand):
                    reg_state = in_state.registers.get(base_reg.index, ValueState.UNINIT)
                    
                    if reg_state == ValueState.UNINIT:
                        self._issues.append(DataflowIssue(
                            pc=pc,
                            code="C001",
                            message=f"Return jump using uninitialized register ${base_reg.index}",
                            severity="error",
                            instruction_text=inst.text,
                        ))
                    elif reg_state == ValueState.DATA:
                        self._issues.append(DataflowIssue(
                            pc=pc,
                            code="C002",
                            message=f"Return jump using data value in ${base_reg.index} instead of return address",
                            severity="error",
                            instruction_text=inst.text,
                        ))
                    elif reg_state == ValueState.UNKNOWN:
                        self._issues.append(DataflowIssue(
                            pc=pc,
                            code="C003",
                            message=f"Return jump using potentially invalid return address in ${base_reg.index}",
                            severity="warning",
                            instruction_text=inst.text,
                        ))
                
                successors.append(-1)
                
        elif opcode == Opcode.HLT:
            pass
            
        else:
            successors.append(pc + 1)
        
        return out_state, successors
    
    def _get_stack_slot_key(self, addr_op: AddressOperand, state: AbstractState) -> int | None:
        eff_offset = normalize_imm8(addr_op.offset)
        if addr_op.base.index == 3:
            return state.sp_offset + eff_offset
        elif addr_op.base.index == 0:
            return 1000 + eff_offset
        return None


def analyze_dataflow(
    ir_program: IRProgram,
    cfg: CFG | None = None,
    *,
    reg_count: int = DEFAULT_REG_COUNT,
) -> DataflowResult:
    if cfg is None:
        cfg = build_cfg(ir_program)
    
    analyzer = DataflowAnalyzer(ir_program, cfg, reg_count=reg_count)
    return analyzer.analyze()
