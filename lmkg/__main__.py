from .cli import Arguments, main as cli_main


def main() -> None:
    """Entry point for `python -m lmkg`.

    This simply forwards to the CLI defined in `cli.py`.
    """
    args = Arguments(explicit_bool=True).parse_args(known_only=True)
    cli_main(args)


if __name__ == "__main__":
    main()
