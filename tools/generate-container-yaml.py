#!/usr/bin/python3

import sys
from typing import Any

from util import ID_PREFIX, RELEASE, BASEONLY, ARCH_SPECIFIC_PACKAGES
import yaml


class literal(str):
    @staticmethod
    def representer(dumper, data):
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')


class folded(str):
    @staticmethod
    def representer(dumper, data):
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='>')


for cls in (literal, folded):
    yaml.add_representer(cls, cls.representer)


def update_container_yaml(template, output, list_file):
    with open(template) as f:
        container_yaml_string = f.read()

    container_yaml_string = container_yaml_string \
        .replace("@ID_PREFIX@", ID_PREFIX) \
        .replace("@RELEASE@", RELEASE)

    container_yaml = yaml.safe_load(container_yaml_string)

    container_yaml["flatpak"]["finish-args"] = folded(container_yaml["flatpak"]["finish-args"])
    container_yaml["flatpak"]["cleanup-commands"] = literal(container_yaml["flatpak"]["cleanup-commands"])

    with open(list_file) as f:
        packages: list[str | Any] = \
            sorted(["flatpak-runtime-config"] + [line.strip() for line in f], key=str.lower)
    print("{}: {} packages".format(template, len(packages)), file=sys.stderr)

    for i, package in enumerate(packages):
        arches = []
        for arch in ARCH_SPECIFIC_PACKAGES:
            if package in ARCH_SPECIFIC_PACKAGES[arch]:
                arches.append(arch)
        if arches:
            packages[i] = {
                "name": package,
                "platforms": {
                    "only": arches
                }
            }

    container_yaml["flatpak"]["packages"] = packages
    with open(output, "w") as f:
        yaml.dump(
            container_yaml, stream=f,
            default_flow_style=False, indent=4, sort_keys=False, encoding="utf-8",
        )


def main():
    if BASEONLY:
        update_container_yaml("container.in.yaml", "container.new.yaml", "out/runtime-base.profile")
        update_container_yaml("container-sdk.in.yaml", "container-sdk.new.yaml", "out/sdk-base.profile")
    else:
        update_container_yaml("container.in.yaml", "container.new.yaml", "out/runtime.profile")
        update_container_yaml("container-sdk.in.yaml", "container-sdk.new.yaml", "out/sdk.profile")


if __name__ == "__main__":
    main()
