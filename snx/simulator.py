from __future__ import annotations

import re
from typing import Callable

from snx.parser import Instruction, parse_code


class SNXSimulator:
    def __init__(
        self,
        code_str: str,
        *,
        reg_count: int = 4,
        mem_size: int = 128,
        trace_callback: Callable[[int, str, list[int]], None] | None = None,
    ):
        self.regs: list[int] = [0] * reg_count
        self.memory: list[int] = [0] * mem_size
        self._reg_initialized: list[bool] = [False] * reg_count
        self._mem_initialized: list[bool] = [False] * mem_size
        self.pc: int = 0
        self.running: bool = True

        self._trace_callback = trace_callback
        self._instructions: list[Instruction]
        self._labels: dict[str, int]
        self._instructions, self._labels = parse_code(code_str)

    @property
    def instructions(self) -> list[Instruction]:
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

    def _get_reg_idx(self, reg_str: str) -> int:
        return int(reg_str.replace("$", ""))

    def _calc_effective_addr(self, addr_str: str) -> int:
        match = re.match(r"(-?\d+)\((\$\d)\)", addr_str)
        if match:
            offset = int(match.group(1))
            reg_idx = self._get_reg_idx(match.group(2))

            # EA <- I + (Rb == $0)? 0 : Rb
            base_val = 0 if reg_idx == 0 else self.regs[reg_idx]
            return offset + base_val
        raise ValueError(f"Invalid address format: {addr_str}")

    def step(self) -> bool:
        if not self.running or self.pc >= len(self._instructions):
            self.running = False
            return False

        inst = self._instructions[self.pc]
        current_pc = self.pc
        self.pc += 1

        self._execute(inst)

        if self._trace_callback:
            self._trace_callback(current_pc, inst.raw, self.regs)

        return self.running

    def _execute(self, inst: Instruction) -> None:
        op = inst.opcode
        args = inst.operands

        if op == "LDA":
            dest = self._get_reg_idx(args[0])
            addr = self._calc_effective_addr(args[1])
            self.regs[dest] = addr
            self._reg_initialized[dest] = True

        elif op == "LD":
            dest = self._get_reg_idx(args[0])
            addr = self._calc_effective_addr(args[1])
            self.regs[dest] = self.memory[addr]
            self._reg_initialized[dest] = True

        elif op == "ST":
            src = self._get_reg_idx(args[0])
            addr = self._calc_effective_addr(args[1])
            self.memory[addr] = self.regs[src]
            self._mem_initialized[addr] = True

        elif op == "ADD":
            dest = self._get_reg_idx(args[0])
            val1 = self.regs[self._get_reg_idx(args[1])]
            val2 = self.regs[self._get_reg_idx(args[2])]
            self.regs[dest] = val1 + val2
            self._reg_initialized[dest] = True

        elif op == "SLT":
            dest = self._get_reg_idx(args[0])
            val1 = self.regs[self._get_reg_idx(args[1])]
            val2 = self.regs[self._get_reg_idx(args[2])]
            self.regs[dest] = 1 if val1 < val2 else 0
            self._reg_initialized[dest] = True

        elif op == "BZ":
            cond_reg = self._get_reg_idx(args[0])
            label = args[1]
            if self.regs[cond_reg] == 0:
                if label not in self._labels:
                    raise ValueError(f"Unknown label: {label}")
                self.pc = self._labels[label]

        elif op == "BAL":
            link_reg = self._get_reg_idx(args[0])
            next_pc = self.pc

            if args[1] in self._labels:
                target_pc = self._labels[args[1]]
            else:
                target_pc = self._calc_effective_addr(args[1])

            self.regs[link_reg] = next_pc
            self._reg_initialized[link_reg] = True
            self.pc = target_pc

        elif op == "HLT":
            self.running = False

        else:
            raise ValueError(f"Unknown opcode: {op}")

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
