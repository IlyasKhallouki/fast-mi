import pytest
from _pipeline import CompiledRoute, compile_route


@pytest.fixture(scope="session")
def full_route_compiled(engine_ready, fd_ready, tmp_path_factory, home_scummvm_guard_factory) -> CompiledRoute:
    """The full Part I plan, built once per session under a tmp dir.

    The object dump comes fresh from the engine, and Fast Downward re-plans.
    Nothing is read from or written to ``out/objects.json`` or ``out/plans/``.
    """
    with home_scummvm_guard_factory():
        return compile_route(tmp_path_factory.mktemp("full-route-plan"))
