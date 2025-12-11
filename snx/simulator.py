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
from snx.word import normalize_imm8, signed16, word

if TYPE_CHECKING:
    from snx.compiler import CompileResult

InputFn = Callable[[], int]
OutputFn = Callable[[int], None]
OobCallbackFn = Callable[[str, int, int, str, int], None]


class SNXSimulator:
    def __init__(
        self,
        ir_program: IRProgram,
        *,
        reg_count: int = DEFAULT_REG_COUNT,
        mem_size: int = DEFAULT_MEM_SIZE,
        trace_callback: Callable[[int, str, list[int]], None] | None = None,
        input_fn: InputFn | None = None,
        output_fn: OutputFn | None = None,
        oob_callback: OobCallbackFn | None = None,
    ):
        self.regs: list[int] = [0] * reg_count
        self.memory: list[int] = [0] * mem_size
        self._reg_initialized: list[bool] = [False] * reg_count
        self._mem_initialized: list[bool] = [False] * mem_size
        self._mem_size = mem_size
        self.pc: int = 0
        self.running: bool = True

        self._trace_callback = trace_callback
        self._input_fn = input_fn
        self._output_fn = output_fn
        self._oob_callback = oob_callback
        self._output_buffer: list[int] = []
        self._ir_program = ir_program
        self._instructions = ir_program.instructions
        self._labels = ir_program.labels

        self._current_pc: int = 0
        self._current_inst_text: str = ""

    @classmethod
    def from_compile_result(
        cls,
        result: "CompileResult",
        *,
        mem_size: int = DEFAULT_MEM_SIZE,
        trace_callback: Callable[[int, str, list[int]], None] | None = None,
        input_fn: InputFn | None = None,
        output_fn: OutputFn | None = None,
        oob_callback: OobCallbackFn | None = None,
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
            input_fn=input_fn,
            output_fn=output_fn,
            oob_callback=oob_callback,
        )

    @classmethod
    def from_source(
        cls,
        code_str: str,
        *,
        reg_count: int = DEFAULT_REG_COUNT,
        mem_size: int = DEFAULT_MEM_SIZE,
        trace_callback: Callable[[int, str, list[int]], None] | None = None,
        input_fn: InputFn | None = None,
        output_fn: OutputFn | None = None,
        oob_callback: OobCallbackFn | None = None,
    ) -> SNXSimulator:
        result = compile_program(code_str, reg_count=reg_count, mem_size=mem_size)
        return cls.from_compile_result(
            result,
            mem_size=mem_size,
            trace_callback=trace_callback,
            input_fn=input_fn,
            output_fn=output_fn,
            oob_callback=oob_callback,
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
        base_val = 0 if base_idx == 0 else self.regs[base_idx]
        eff_offset = normalize_imm8(operand.offset)
        return word(base_val + eff_offset)

    def _set_reg(self, index: int, value: int) -> None:
        self.regs[index] = word(value)
        self._reg_initialized[index] = True

    def _notify_oob(self, kind: str, addr: int) -> None:
        if self._oob_callback is not None:
            self._oob_callback(
                kind,
                addr,
                self._current_pc,
                self._current_inst_text,
                self._mem_size,
            )

    def _set_mem(self, addr: int, value: int) -> None:
        if 0 <= addr < self._mem_size:
            self.memory[addr] = word(value)
            self._mem_initialized[addr] = True
            return
        self._notify_oob("store", addr)

    def _load_mem(self, addr: int) -> int:
        if 0 <= addr < self._mem_size:
            return self.memory[addr]
        self._notify_oob("load", addr)
        return 0

    def _read_input(self) -> int:
        if self._input_fn is not None:
            return word(self._input_fn())
        return 0

    def _write_output(self, value: int) -> None:
        w = word(value)
        self._output_buffer.append(w)
        if self._output_fn is not None:
            self._output_fn(w)

    def get_output_buffer(self) -> list[int]:
        return list(self._output_buffer)

    def step(self) -> bool:
        if not self.running or self.pc >= len(self._instructions):
            self.running = False
            return False

        inst = self._instructions[self.pc]
        current_pc = self.pc
        self.pc += 1

        self._current_pc = current_pc
        self._current_inst_text = inst.text

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
                self._set_reg(dest.index, addr)

        elif op == Opcode.LD:
            dest = operands[0]
            addr_op = operands[1]
            if isinstance(dest, RegisterOperand) and isinstance(addr_op, AddressOperand):
                addr = self._calc_effective_addr(addr_op)
                self._set_reg(dest.index, self._load_mem(addr))

        elif op == Opcode.ST:
            src = operands[0]
            addr_op = operands[1]
            if isinstance(src, RegisterOperand) and isinstance(addr_op, AddressOperand):
                addr = self._calc_effective_addr(addr_op)
                self._set_mem(addr, self.regs[src.index])

        elif op == Opcode.ADD:
            rd, rsa, rsb = operands[0], operands[1], operands[2]
            if isinstance(rd, RegisterOperand) and isinstance(rsa, RegisterOperand) and isinstance(rsb, RegisterOperand):
                self._set_reg(rd.index, self.regs[rsa.index] + self.regs[rsb.index])

        elif op == Opcode.AND:
            rd, rsa, rsb = operands[0], operands[1], operands[2]
            if isinstance(rd, RegisterOperand) and isinstance(rsa, RegisterOperand) and isinstance(rsb, RegisterOperand):
                self._set_reg(rd.index, self.regs[rsa.index] & self.regs[rsb.index])

        elif op == Opcode.SUB:
            rd, rsa, rsb = operands[0], operands[1], operands[2]
            if isinstance(rd, RegisterOperand) and isinstance(rsa, RegisterOperand) and isinstance(rsb, RegisterOperand):
                self._set_reg(rd.index, self.regs[rsa.index] - self.regs[rsb.index])

        elif op == Opcode.SLT:
            rd, rsa, rsb = operands[0], operands[1], operands[2]
            if isinstance(rd, RegisterOperand) and isinstance(rsa, RegisterOperand) and isinstance(rsb, RegisterOperand):
                val_a = signed16(self.regs[rsa.index])
                val_b = signed16(self.regs[rsb.index])
                self._set_reg(rd.index, 1 if val_a < val_b else 0)

        elif op == Opcode.NOT:
            rd, rs = operands[0], operands[1]
            if isinstance(rd, RegisterOperand) and isinstance(rs, RegisterOperand):
                self._set_reg(rd.index, ~self.regs[rs.index])

        elif op == Opcode.SR:
            rd, rs = operands[0], operands[1]
            if isinstance(rd, RegisterOperand) and isinstance(rs, RegisterOperand):
                self._set_reg(rd.index, self.regs[rs.index] >> 1)

        elif op == Opcode.IN:
            dest = operands[0]
            if isinstance(dest, RegisterOperand):
                self._set_reg(dest.index, self._read_input())

        elif op == Opcode.OUT:
            src = operands[0]
            if isinstance(src, RegisterOperand):
                self._write_output(self.regs[src.index])

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

                self._set_reg(link_reg.index, next_pc)
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
