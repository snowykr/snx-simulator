import sys

from snx.sample_runner import run_sample_program


def main() -> None:
    exit_code = run_sample_program()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
