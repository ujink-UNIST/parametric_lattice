# apdl_block.py

from core.apdl_commands import ApdlCommands


from textwrap import dedent

INLINE_COMMENT_PREFIX = "!<"
COMMENT_STOPS = (32, 48, 64, 80, 96, 112)


def _comment_column(code_len: int) -> int:
    for stop in COMMENT_STOPS:
        if code_len < stop:
            return stop

    return COMMENT_STOPS[-1]


def apdl_block(text: str) -> tuple[str, ...]:
    lines = dedent(text).splitlines()

    result: list[str] = []

    previous_blank = False

    for line in lines:
        line = line.rstrip()

        is_blank = not line

        # 연속 빈 줄만 제거
        if is_blank:
            if previous_blank:
                continue

            result.append("")
            previous_blank = True
            continue

        previous_blank = False

        if INLINE_COMMENT_PREFIX in line:
            code, comment = line.split(
                INLINE_COMMENT_PREFIX,
                1,
            )

            code = code.rstrip()
            comment = comment.rstrip()

            column = _comment_column(len(code))

            formatted = f"{code:<{column}}" f"! {comment}"

            result.append(formatted)

        else:
            result.append(line)

    return tuple(result)


def apdl_section(title: str) -> str:
    line = "=" * 60
    return f"""
! {line}
! {title}
! {line}
""".strip()


def apdl_comment(text: str) -> str:
    return f"! --- {text}"


def apdl_inline_comment(text: str) -> str:
    return f"{INLINE_COMMENT_PREFIX}{text}"
