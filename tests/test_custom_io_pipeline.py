from custom_io import apdl_io
from custom_io.pipeline import run_apdl_commands


class _FakeMapdl:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.stopped = False

    def run(self, command: str) -> None:
        self.commands.append(command)

    def exit(self) -> None:
        self.stopped = True


def test_apdl_io_run_commands_and_stop_mapdl():
    mapdl = _FakeMapdl()

    apdl_io.run_commands(mapdl, ("FINISH", "/CLEAR"))
    apdl_io.stop_mapdl(mapdl)

    assert mapdl.commands == ["FINISH", "/CLEAR"]
    assert mapdl.stopped is True


def test_apdl_io_run_commands_supports_pipeline_steps():
    mapdl = _FakeMapdl()

    def custom_step(mapdl_obj) -> None:
        mapdl_obj.run("SOLVE")

    apdl_io.run_commands(
        mapdl,
        (("FINISH", "/CLEAR"), custom_step, ("POST1",)),
    )

    assert mapdl.commands == [
        "FINISH",
        "/CLEAR",
        "SOLVE",
        "POST1",
    ]


def test_run_apdl_commands_uses_apdl_io_boundary(monkeypatch):
    mapdl = _FakeMapdl()
    launch_kwargs_seen = {}

    def fake_start_mapdl(**kwargs):
        launch_kwargs_seen.update(kwargs)
        return mapdl

    monkeypatch.setattr(apdl_io, "start_mapdl", fake_start_mapdl)

    run_apdl_commands(
        ("ET,1,188", "SOLVE"),
        jobname="unit-test",
    )

    assert launch_kwargs_seen == {"jobname": "unit-test"}
    assert mapdl.commands == ["ET,1,188", "SOLVE"]
    assert mapdl.stopped is True
