from dataclasses import dataclass

import pants.core.goals.package
from pants.core.goals.package import (
    BuiltPackage,
    BuiltPackageArtifact,
    OutputPathField,
)
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    BoolField,
    Dependencies,
    DependenciesRequest,
    DescriptionField,
    HydratedSources,
    HydrateSourcesRequest,
    StringField,
    StringSequenceField,
    Tags,
    Target,
    Targets,
    TransitiveTargets,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionRule


class BaseImage(StringField):
    alias = "base_image"
    required = True
    help = "This is used to set the Base Image for all future pants build steps (e.g. python:3.8.8-slim-buster)"


class DockerIgnore(StringSequenceField):
    alias = "docker_ignore"
    required = False
    default = []
    help = "A list of directories to exclude from the docker build context, each entry should be a valid line in a .dockerignore file"


class ImageSetup(StringSequenceField):
    alias = "image_setup_commands"
    required = False
    default = []
    help = 'Commands to run in the image during the build process. Each will be evaluated as it\'s own process in the container and will create a new layer in the resulting image (e.g. ["apt-get update && apt-get upgrade --yes", "apt-get -y install gcc libpq-dev"],)'


class WorkDir(StringField):
    alias = "workdir"
    required = False
    default = "container"
    help = "The directory inside the container into which"


class Registry(StringField):
    alias = "registry"
    required = False
    help = "The registry of the resulting docker image"


class CacheFrom(StringField):
    alias = "cache_from"
    required = False
    default = None
    help = (
        "Specify a registry that will be used for caching via the "
        "docker build --cache-from option (requires BuildKit to be installed)"
    )


class BuildkitInlineCache(BoolField):
    alias = "buildkit_inline_cache"
    required = False
    default = False
    help = (
        "Enables writing an inline layer cache for the image via the docker build --build-arg "
        "BUILDKIT_INLINE_CACHE=1 parameter (requires BuildKit to be installed)"
    )


class Tags(StringSequenceField):
    alias = "tags"
    default = []
    required = False
    help = 'A list of tags to apply to the resulting docker image (e.g. ["1.0.0", "main"]) '


class Command(StringSequenceField):
    alias = "command"
    default = []
    required = False
    help = "Command used to run the Docker container"


@dataclass(frozen=True)
class DockerPackageFieldSet(pants.core.goals.package.PackageFieldSet):
    alias = "docker_field_set"
    required_fields = (BaseImage,)

    base_image: BaseImage
    image_setup: ImageSetup
    ignore: DockerIgnore
    registry: Registry
    cache_from: CacheFrom
    buildkit_inline_cache: BuildkitInlineCache
    tags: Tags
    dependencies: Dependencies
    workdir: WorkDir
    command: Command
    output_path: OutputPathField


class Docker(Target):
    help = "A docker image that will contain all the source files of its transitive dependencies"
    alias = "docker"
    core_fields = (
        DescriptionField,
        Dependencies,
        BaseImage,
        ImageSetup,
        OutputPathField,
        WorkDir,
        Tags,
        Command,
        CacheFrom,
        BuildkitInlineCache,
    )


def rules():
    return [
        UnionRule(
            pants.core.goals.package.PackageFieldSet, DockerPackageFieldSet
        )
    ]
