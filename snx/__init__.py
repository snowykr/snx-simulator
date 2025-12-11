from snx.simulator import SNXSimulator
from snx.parser import Instruction, parse_code
from snx.compiler import compile_program, CompileResult
from snx.trace import format_trace_header, format_trace_row
from snx.cfg import CFG, build_cfg
from snx.dataflow import DataflowResult, analyze_dataflow
from snx.checker import check_program, CheckResult
from snx.word import (
    word,
    signed16,
    WORD_MASK,
    WORD_BITS,
    IMM8_MASK,
    imm8,
    signed8,
    normalize_imm8,
)
from snx.encoding import (
    encode_instruction,
    encode_program,
    decode_word,
    format_hex,
    format_intel_hex,
    OPCODE_TO_INT,
    INT_TO_OPCODE,
    EncodingError,
)

__all__ = [
    "SNXSimulator",
    "Instruction",
    "parse_code",
    "compile_program",
    "CompileResult",
    "format_trace_header",
    "format_trace_row",
    "CFG",
    "build_cfg",
    "DataflowResult",
    "analyze_dataflow",
    "check_program",
    "CheckResult",
    "word",
    "signed16",
    "WORD_MASK",
    "WORD_BITS",
    "IMM8_MASK",
    "imm8",
    "signed8",
    "normalize_imm8",
    "encode_instruction",
    "encode_program",
    "decode_word",
    "format_hex",
    "format_intel_hex",
    "OPCODE_TO_INT",
    "INT_TO_OPCODE",
    "EncodingError",
]
