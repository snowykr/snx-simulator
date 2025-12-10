from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from snx.ast import (
    AddressOperand,
    InstructionIR,
    IRProgram,
    LabelRefOperand,
    Opcode,
    RegisterOperand,
)
from snx.compiler import compile_program
from snx.constants import DEFAULT_MEM_SIZE, DEFAULT_REG_COUNT

if TYPE_CHECKING:
    from snx.compiler import CompileResult


class SNXSimulator:
    def __init__(
        self,
        ir_program: IRProgram,
        *,
        reg_count: int = DEFAULT_REG_COUNT,
        mem_size: int = DEFAULT_MEM_SIZE,
        trace_callback: Callable[[int, str, list[int]], None] | None = None,
    ):
        self.regs: list[int] = [0] * reg_count
        self.memory: list[int] = [0] * mem_size
        self._reg_initialized: list[bool] = [False] * reg_count
        self._mem_initialized: list[bool] = [False] * mem_size
        self.pc: int = 0
        self.running: bool = True

        self._trace_callback = trace_callback
        self._ir_program = ir_program
        self._instructions = ir_program.instructions
        self._labels = ir_program.labels

    @classmethod
    def from_compile_result(
        cls,
        result: "CompileResult",
        *,
        mem_size: int = DEFAULT_MEM_SIZE,
        trace_callback: Callable[[int, str, list[int]], None] | None = None,
    ) -> SNXSimulator:
        if result.has_errors():
            raise ValueError(
                f"Cannot create simulator from CompileResult with errors:\n"
                f"{result.format_diagnostics()}"
            )
        if result.ir is None:
            raise ValueError("CompileResult contains no IR.")
        return cls(
            result.ir,
            reg_count=result.reg_count,
            mem_size=mem_size,
            trace_callback=trace_callback,
        )

    @classmethod
    def from_source(
        cls,
        code_str: str,
        *,
        reg_count: int = DEFAULT_REG_COUNT,
        mem_size: int = DEFAULT_MEM_SIZE,
        trace_callback: Callable[[int, str, list[int]], None] | None = None,
    ) -> SNXSimulator:
        result = compile_program(code_str, reg_count=reg_count)
        return cls.from_compile_result(
            result,
            mem_size=mem_size,
            trace_callback=trace_callback,
        )

    @property
    def instructions(self) -> tuple[InstructionIR, ...]:
        return self._instructions

    @property
    def labels(self) -> dict[str, int]:
        return self._labels

    def get_state(self) -> dict:
        return {
            "pc": self.pc,
            "regs": list(self.regs),
            "running": self.running,
        }

    def _calc_effective_addr(self, operand: AddressOperand) -> int:
        base_idx = operand.base.index
        # EA <- I + (Rb == $0)? 0 : Rb
        base_val = 0 if base_idx == 0 else self.regs[base_idx]
        return operand.offset + base_val

    def step(self) -> bool:
        if not self.running or self.pc >= len(self._instructions):
            self.running = False
            return False

        inst = self._instructions[self.pc]
        current_pc = self.pc
        self.pc += 1

        self._execute(inst)

        if self._trace_callback:
            self._trace_callback(current_pc, inst.text, list(self.regs))

        return self.running

    def _execute(self, inst: InstructionIR) -> None:
        op = inst.opcode
        operands = inst.operands

        if op == Opcode.LDA:
            dest = operands[0]
            addr_op = operands[1]
            if isinstance(dest, RegisterOperand) and isinstance(addr_op, AddressOperand):
                addr = self._calc_effective_addr(addr_op)
                self.regs[dest.index] = addr
                self._reg_initialized[dest.index] = True

        elif op == Opcode.LD:
            dest = operands[0]
            addr_op = operands[1]
            if isinstance(dest, RegisterOperand) and isinstance(addr_op, AddressOperand):
                addr = self._calc_effective_addr(addr_op)
                self.regs[dest.index] = self.memory[addr]
                self._reg_initialized[dest.index] = True

        elif op == Opcode.ST:
            src = operands[0]
            addr_op = operands[1]
            if isinstance(src, RegisterOperand) and isinstance(addr_op, AddressOperand):
                addr = self._calc_effective_addr(addr_op)
                self.memory[addr] = self.regs[src.index]
                self._mem_initialized[addr] = True

        elif op == Opcode.ADD:
            rd, rsa, rsb = operands[0], operands[1], operands[2]
            if isinstance(rd, RegisterOperand) and isinstance(rsa, RegisterOperand) and isinstance(rsb, RegisterOperand):
                self.regs[rd.index] = self.regs[rsa.index] + self.regs[rsb.index]
                self._reg_initialized[rd.index] = True

        elif op == Opcode.AND:
            rd, rsa, rsb = operands[0], operands[1], operands[2]
            if isinstance(rd, RegisterOperand) and isinstance(rsa, RegisterOperand) and isinstance(rsb, RegisterOperand):
                self.regs[rd.index] = self.regs[rsa.index] & self.regs[rsb.index]
                self._reg_initialized[rd.index] = True

        elif op == Opcode.SLT:
            rd, rsa, rsb = operands[0], operands[1], operands[2]
            if isinstance(rd, RegisterOperand) and isinstance(rsa, RegisterOperand) and isinstance(rsb, RegisterOperand):
                self.regs[rd.index] = 1 if self.regs[rsa.index] < self.regs[rsb.index] else 0
                self._reg_initialized[rd.index] = True

        elif op == Opcode.NOT:
            rd, rs = operands[0], operands[1]
            if isinstance(rd, RegisterOperand) and isinstance(rs, RegisterOperand):
                self.regs[rd.index] = ~self.regs[rs.index]
                self._reg_initialized[rd.index] = True

        elif op == Opcode.SR:
            rd, rs = operands[0], operands[1]
            if isinstance(rd, RegisterOperand) and isinstance(rs, RegisterOperand):
                self.regs[rd.index] = self.regs[rs.index] >> 1
                self._reg_initialized[rd.index] = True

        elif op == Opcode.BZ:
            cond_reg = operands[0]
            label_op = operands[1]
            if isinstance(cond_reg, RegisterOperand) and isinstance(label_op, LabelRefOperand):
                if self.regs[cond_reg.index] == 0:
                    self.pc = self._labels[label_op.name]

        elif op == Opcode.BAL:
            link_reg = operands[0]
            target_op = operands[1]
            if isinstance(link_reg, RegisterOperand):
                next_pc = self.pc

                if isinstance(target_op, LabelRefOperand):
                    target_pc = self._labels[target_op.name]
                elif isinstance(target_op, AddressOperand):
                    target_pc = self._calc_effective_addr(target_op)
                else:
                    target_pc = self.pc

                self.regs[link_reg.index] = next_pc
                self._reg_initialized[link_reg.index] = True
                self.pc = target_pc

        elif op == Opcode.HLT:
            self.running = False

    def get_reg_init_flags(self) -> tuple[bool, ...]:
        return tuple(self._reg_initialized)

    def get_memory_init_flags(self) -> tuple[bool, ...]:
        return tuple(self._mem_initialized)

    def run(self, max_steps: int | None = None) -> None:
        steps = 0
        while self.running:
            if max_steps is not None and steps >= max_steps:
                break
            self.step()
            steps += 1
