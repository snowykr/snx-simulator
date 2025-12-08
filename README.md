# SN-X Simulator

## 개요
SN-X Simulator는 SN/X 아키텍처를 파이썬으로 구현한 CPU 시뮬레이터입니다.

## 요구 사항
- Python 3.11 이상
- [uv](https://github.com/astral-sh/uv)

## 설치
1. uv 설치 (설치되어 있지 않은 경우)
   ```bash
   pip install uv
   ```
2. 가상환경 생성 및 활성화
   ```bash
   uv venv
   source .venv/bin/activate
   ```
3. 프로젝트 종속성 설치
   ```bash
   uv pip install -e .
   ```

## 실행
샘플 어셈블리를 포함한 메인 스크립트를 실행하면 트레이스 테이블과 함께 시뮬레이션 결과를 확인할 수 있습니다.
```bash
uv run python main.py
```

## 아키텍처 및 명령어 요약
- 레지스터: `$0`~`$3`, `$0`은 주소 계산 시 0으로 고정됩니다.
- 메모리: 128워드 고정 배열을 사용합니다.
- 명령어: `LDA`, `LD`, `ST`, `ADD`, `SLT`, `BZ`, `BAL`, `HLT` 등을 지원하며, 각 명령어는 `parse_code`로 파싱된 후 `step()` 루프에서 실행됩니다.
- 트레이스: 각 스텝마다 PC, 명령어, 레지스터 상태를 표 형태로 출력합니다.
