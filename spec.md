# **SN/X 아키텍처의 설계 명세(Specification)**

**교과서, Makefile 구조, 그리고 snxasm의 소스 코드(y, l, h)**를 100% 팩트 기반으로 분석하여, 컴파일러 구현과 문서화에 필요한 **SN/X 아키텍처 기술 명세서(Technical Reference)**입니다.
이 내용은 Python 컴파일러의 백엔드(Code Generator)를 설계할 때 기준이 되는 데이터입니다.

-----

# 1\. SN/X 아키텍처 기술 명세서 (Technical Specification)

## 1.1 시스템 개요 (System Overview)

  * **아키텍처 명칭:** Simple 16bit Non-Pipeline Processor (SN/X)
  * **버전:** V1.1 (소스코드 헤더 기준)
  * **데이터 폭 (Word Size):** 16-bit
  * **메모리 구조:** Harvard Architecture 유사 구조
      * **명령어 메모리 (IMEM):** 16-bit 주소 공간 ($2^{16}$ 워드)
      * **데이터 메모리 (DMEM):** 16-bit 주소 공간 ($2^{16}$ 워드)
      * **주소 지정 단위:** Word Addressing (주소 1 증가는 16-bit 이동을 의미)
  * **파이프라인:** 없음 (Non-Pipeline, 순차 실행)

## 1.2 레지스터 파일 (Register File)

총 4개의 16-bit 범용 레지스터를 가집니다.

| 레지스터 명 | 주소 (2bit) | 역할 및 특징 |
| :--- | :---: | :--- |
| **$0** | `00` | 범용 레지스터 / **I-형식 명령어에서 Base로 사용 시 '0'으로 취급** (인덱싱 없음) |
| **$1** | `01` | 범용 레지스터 |
| **$2** | `10` | 범용 레지스터 |
| **$3** | `11` | 범용 레지스터 |
| **PC** | - | 프로그램 카운터 (16-bit), 프로그래머가 직접 접근 불가 |

> **주의 (Compiler impl. note):** MIPS와 달리 `$0`에 값을 쓸 수 있고 저장도 됩니다. 단, `LD $1, 10($0)` 처럼 메모리 주소 계산의 **Base Register** 자리에 `$0`이 오면, 레지스터 값이 아닌 상수 `0`으로 처리되어 `MEM[10]`을 참조하게 됩니다.

## 1.3 명령어 형식 (Instruction Formats)

모든 명령어는 **16-bit 고정 길이**입니다. 컴파일러 백엔드는 아래 비트맵에 맞춰 바이너리를 생성해야 합니다.

### **Type R (Register Operation)**

레지스터 간 연산을 수행합니다.

  * **어셈블리:** `OP R1, R2, R3` (R1 $\leftarrow$ R2 `OP` R3)
  * **비트맵:**
    ```text
    | 15 ... 12 | 11 ... 10 |  9 ... 8  |  7 ... 6  | 5 ... 0 |
    |  OP Code  | Src1 (R2) | Src2 (R3) | Dest (R1) | Unused  |
    ```

### **Type R1 (1 Source Register)**

단항 연산(NOT, Shift 등)을 수행합니다.

  * **어셈블리:** `OP R1, R2` (R1 $\leftarrow$ `OP` R2)
  * **비트맵:**
    ```text
    | 15 ... 12 | 11 ... 10 |  9 ... 8  |  7 ... 6  | 5 ... 0 |
    |  OP Code  | Src  (R2) |  Unused   | Dest (R1) | Unused  |
    ```

### **Type R0 (No Operand)**

오퍼랜드가 없는 제어 명령어입니다.

  * **어셈블리:** `OP`
  * **비트맵:**
    ```text
    | 15 ... 12 | 11 .................. 0 |
    |  OP Code  |        Unused           |
    ```

### **Type I (Immediate / Memory)**

메모리 접근, 분기, 상수 연산에 사용됩니다.

  * **어셈블리:** `OP R1, Imm(R2)` 또는 `OP R1, Label`
  * **비트맵:**
    ```text
    | 15 ... 12 | 11 ... 10 |  9 ... 8  | 7 ........... 0 |
    |  OP Code  | Dest (R1) | Base (R2) | Immediate (8bit)|
    ```
      * **Base (R2):** 이 값이 `00($0)`이면 `Base`값은 0이 되어 `Immediate`가 절대 주소가 됩니다.
      * **Immediate:** 8비트 크기 (0\~255 또는 -128\~127).

-----

## 1.4 명령어 세트 (Instruction Set & Opcode Map)

`snxasm.l` 파일을 통해 확정된 Opcode 매핑 테이블입니다. 컴파일러 구현 시 이 값을 매핑해야 합니다.

| Mnemonic | Opcode (Hex) | Type | 동작 설명 (Operation) |
| :--- | :---: | :---: | :--- |
| **ADD** | `0x0` | R | `R1 = R2 + R3` |
| **AND** | `0x1` | R | `R1 = R2 & R3` (Bitwise AND) |
| **SUB** | `0x2` | R | `R1 = R2 - R3` |
| **SLT** | `0x3` | R | `R1 = (R2 < R3) ? 1 : 0` (Set Less Than) |
| **NOT** | `0x4` | R1 | `R1 = ~R2` (Bitwise NOT) |
| **SR** | `0x6` | R1 | `R1 = R2 >> 1` (Shift Right, 1bit 추정) |
| **HLT** | `0x7` | R0 | 프로세서 정지 (Halt) |
| **LD** | `0x8` | I | `R1 = MEM[Base + Imm]` (Load Word) |
| **ST** | `0x9` | I | `MEM[Base + Imm] = R1` (Store Word) |
| **LDA** | `0xA` | I | `R1 = Base + Imm` (Load Address / 상수 로드) |
| **IN** | `0xC` | I | `R1 = Input_Port` (입력) |
| **OUT** | `0xD` | I | `Output_Port = R1` (출력) |
| **BZ** | `0xE` | I | `if (R1 == 0) PC = PC + Imm` (Branch if Zero) |
| **BAL** | `0xF` | I | `R1 = PC + 1; PC = PC + Imm` (Branch and Link, 함수호출) |

-----

# 2\. README.md 추가용 정보

프로젝트의 `README.md`에 포함시킬 수 있도록 정리한 아키텍처 설명 섹션입니다.

```markdown
## SN/X Architecture Overview

SN/X (Simple 16bit Non-Pipeline Processor) is a strictly 16-bit RISC processor designed for educational purposes, featuring a simplified instruction set and Harvard-style memory architecture.

### Key Specifications
- **Data Width:** 16-bit
- **Address Space:** 16-bit ($2^{16}$ Words) for both Instruction and Data Memory.
- **Registers:** 4 General Purpose Registers (16-bit).
  - `$0`, `$1`, `$2`, `$3`
  - Note: `$0` is treated as value `0` only when used as a base register in memory addressing modes.
- **Pipeline:** Non-Pipelined (Single-cycle or Multi-cycle sequential execution).

### Instruction Formats
All instructions are 16-bit fixed length.

| Type | Format | Layout (Bits 15-0) |
| :--- | :--- | :--- |
| **R** | `OP R1, R2, R3` | `OP(4) | Src1(2) | Src2(2) | Dest(2) | Unused(6)` |
| **R1** | `OP R1, R2` | `OP(4) | Src(2) | Unused(2) | Dest(2) | Unused(6)` |
| **I** | `OP R1, Imm(R2)`| `OP(4) | Dest(2) | Base(2) | Imm(8)` |

### Instruction Set Summary
| Opcode | Mnemonic | Function |
| :---: | :--- | :--- |
| `0x0` | **ADD** | Arithmetic Add |
| `0x1` | **AND** | Bitwise AND |
| `0x2` | **SUB** | Arithmetic Subtract |
| `0x3` | **SLT** | Set on Less Than |
| `0x4` | **NOT** | Bitwise NOT |
| `0x6` | **SR** | Shift Right |
| `0x7` | **HLT** | Halt Processor |
| `0x8` | **LD** | Load Word from Memory |
| `0x9` | **ST** | Store Word to Memory |
| `0xA` | **LDA** | Load Address (Immediate calculation) |
| `0xC` | **IN** | Input from Port |
| `0xD` | **OUT** | Output to Port |
| `0xE` | **BZ** | Branch if Zero |
| `0xF` | **BAL** | Branch and Link (Function Call) |
```

이 정보들은 실제 snxasm의 파서 로직 및 어휘 분석기 소스 코드와 교과서 내용으로부터 추출한 내용입니다.