import subprocess
import sys


def test_cli_executes_program_with_dw_data(tmp_path):
    asm_file = tmp_path / "test_dw.s"
    asm_file.write_text(
        "main:\n    LD $1, my_data\n    ADD $1, $1, $1\n    OUT $1\n    HLT\nmy_data: DW 21",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "snx.cli", str(asm_file)],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "OUT $1" in result.stdout
    assert "42" in result.stdout
    assert "Execution completed successfully" in result.stdout
    assert result.returncode == 0


def test_cli_reports_cross_domain_label_error_for_dw_program(tmp_path):
    asm_file = tmp_path / "error_dw.s"
    asm_file.write_text(
        "main:\n    BZ $0, my_data\n    HLT\nmy_data: DW 42", encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, "-m", "snx.cli", str(asm_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Build failed" in result.stdout
    assert "[S008]" in result.stdout
    assert "Data label 'my_data' cannot be used as a code target" in result.stdout


def test_cli_reports_code_label_as_data_error(tmp_path):
    asm_file = tmp_path / "error_code.s"
    asm_file.write_text("main:\n    LD $1, main\n    HLT", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "snx.cli", str(asm_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Build failed" in result.stdout
    assert "[S007]" in result.stdout
    assert "Code label 'main' cannot be used as a data address" in result.stdout
