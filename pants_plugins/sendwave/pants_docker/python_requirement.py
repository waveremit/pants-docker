import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from pants.backend.python.subsystems.repos import PythonRepos
from pants.backend.python.subsystems.setup import PythonSetup
from pants.backend.python.target_types import PythonRequirementsField
from pants.engine.fs import Digest, GlobMatchErrorBehavior, PathGlobs
from pants.engine.rules import Get, collect_rules, rule
from sendwave.pants_docker.docker_component import (
    DockerComponent,
    DockerComponentFieldSet,
)
from sendwave.pants_docker.subsystem import Docker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VirtualEnvRequest:
    enable_resolves: bool
    requirement_constraints: Optional[str]


@rule
async def create_virtual_env(
    resolve_request: VirtualEnvRequest,
) -> DockerComponent:
    assert (
        not resolve_request.enable_resolves
    ), "Pants lockfiles not yet supported"

    copy_command = []
    sources = None
    pip_upgrade_constraint = ""
    if constraint_file := resolve_request.requirement_constraints:

        sources = await Get(
            Digest,
            PathGlobs(
                [constraint_file],
                glob_match_error_behavior=GlobMatchErrorBehavior.error,
                description_of_origin="the option `requirement_constraints`",
            ),
        )
        pip_upgrade_constraint = " -c {}".format(constraint_file)
        copy_command.append("COPY application/{} .\n".format(constraint_file))
    return DockerComponent(
        commands=tuple(
            [
                *copy_command,
                "RUN python -m venv --upgrade /.virtual_env\n",
                "ENV PATH=/.virtual_env/bin:$PATH\n",
                "ENV VIRTUAL_ENV=/.virtual_env\n",
                "RUN python -m pip install --upgrade pip{}\n".format(
                    pip_upgrade_constraint
                ),
            ]
        ),
        sources=sources,
    )


@dataclass(frozen=True)
class PythonRequirements:
    requirements: Tuple[PythonRequirementsField]


@rule
async def get_requirements(
    field_set: PythonRequirements,
    setup: PythonSetup,
    repos: PythonRepos,
    docker: Docker,
) -> DockerComponent:
    install_args = _get_install_args(setup, repos)
    if docker.options.multiline_pip_install:
        commands = tuple(
            "RUN python -m pip install {} {} {} {}\n".format(
                install_args.index_args,
                install_args.links_args,
                install_args.constraint_arg,
                lib,
            )
            for lib in field_set.requirements
        )
    else:
        commands = (
            f"RUN python -m pip install {install_args.index_args} "
            + f"{install_args.links_args} {install_args.constraint_arg} "
            + " ".join(str(lib) for lib in field_set.requirements)
            + "\n"
        )
    return DockerComponent(
        commands=commands,
        sources=None,
    )


@dataclass
class PipInstallArgs:
    links_args: str
    index_args: str
    constraint_arg: str


def _get_install_args(
    setup: PythonSetup,
    repos: PythonRepos,
) -> PipInstallArgs:
    assert not setup.enable_resolves, "Pants lockfiles not yet supported"
    if repos.repos:
        links_args = " ".join(
            "--find-links {}".format(repo for repo in repos.repos)
        )
    else:
        links_args = ""
    num_indices = len(repos.indexes)
    if num_indices >= 1:
        index_args = f"--index-url {repos.indexes[0]}"
    if num_indices > 1:
        index_args = index_args + " ".join(
            [f"--extra-index-url {url}" for url in repos.indexes[1:]]
        )
    if num_indices == 0:
        index_args = " --no-index "
    constraint_arg = ""
    if setup.requirement_constraints:
        constraint_arg = f"--constraint {setup.requirement_constraints}"
    return PipInstallArgs(
        links_args=links_args,
        index_args=index_args,
        constraint_arg=constraint_arg,
    )


def rules():
    return [*collect_rules()]
