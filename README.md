# flatpaks/flatpak-runtime

This git repository holds container definition file for the Fedora Flatpak runtimes.
It also holds scripts and data files used to maintain and update the Fedora Flatpak runtimes.

## Updating

*Prequisites*: you need to have the following "upstream" runtimes installed:

* `org.freedesktop.Platform/x86_64/24.08`
* `org.freedesktop.Sdk/x86_64/24.08`
* `org.gnome.Platform/x86_64/47`
* `org.gnome.Sdk/x86_64/47`

You also need `python3-jinja2` and possibly a few other Python
packages installed.

And finally, you'll need to have
[flatpak-container-tools](https://gitlab.com/flatpak-container/flatpak-container-tools) installed.

*How it works*: The files in the upstream runtimes are the primary source for the contents
of the corresponding Fedora runtimes. When you type `make update`, the
steps are as follows:

* List the contents of selected directories of the upstream runtime
  (`tools/list-files.py`)
* Exclude and rename files, and otherwise tweak the contents of the
  resulting lists, and find the Fedora packages that contain the
  corresponding packages. (`tools/resolve-files.py`)
* Find all dependencies of the resolved packages using `flatpak-container-depchase resolve-requires`,
  correlate it all together, figure out the install profiles for each runtime,
  and create `report/runtime.html`. (`tools/generate-runtime-report.py`)
* Create a `container.new.yaml` using the profiles. (`tools/generate-container-yaml.py`)
* Finds data about applications packaged in Fedora and Flathub
  (`tools/download-fedora-appstream.sh`, `tools/download-flathub-appstream.sh`,
  `tools/download-reviews.py`)
* Finds out how those applications would build using this runtime, and generates more reports
  in `reports/`. (`tools/generate-app-reports.py`).
* Copy `container.new.yaml` to `container.yaml`

*Report generation*: if you type `make report` instead then all the above happens
except the last step.

## Viewing the HTML reports

Because the application reports dynamically load generated JSON files, they can't
be viewed as local files. You can run a web server to view them like:

``` sh
podman run -it --rm -p 8081:8080 \
   -v $(pwd)/reports:/usr/share/nginx/html:ro,z \
   docker.io/nginxinc/nginx-unprivileged \
   nginx -g 'daemon off;'
```

And then go to [https://localhost:8081/applications.html].

## Tweaking the result

The main way to tweak the result is to edit and extend the data embedded in
`tools/resolve-files.py`. Make sure you add comments explaining why you are
excluding files, and feed back exclusions to the upstream runtime maintainers
as appropriate.

## Package notes

To aid in keeping track of the status of all the packages in
`report.html`, notes and "flags" are read from package-notes.txt. The
notes are added to `report.html` and the flags affect formatting. The
top of that file has a comment describing the simple format.

## Repository structure

This "main" branch of the repository is maintained at:

  [https://gitlab.com/fedora/sigs/flatpak/flatpak-runtime-scripts]

The configuration files in scripts in the main branch are meant to work
with:

* the latest version of the Freedesktop SDK
* the latest version of the GNOME SDK
* the latest version of Fedora that has a runtime built for it
  (stable or branched).
* the latest version of centos-stream that has a runtime built for it
  (stable or the in-development version)

If the code and package-notes.txt can't be made to work with both
the applicable version of Fedora and the applicable version of
centos-stream, then Fedora takes precendence, and compatibility with
centos stream is fixed up in the appropriate branch.

The generated container.yaml and container-sdk.yaml files are not
committed to the main branch.

Once work starts on a runtime for a particular OS release, a branch
is created for that release (f41, c10s, etc.).

These branches have container.yaml and container-sdk.yaml on them, and
include. Until the runtime is released, work is done on the main
branch and merged into these branches. (container.yaml and
container-sdk.yaml should be updated as part of the merge request.)

After release merging stops, and the branch contains:

* Cherry-picked fixes from the main branch that maintain compatibility
* Fixes specific to that operating version
* package-notes.txt additions needed to maintain runtime compatibility
  (if a dependency pulling in a package is removed after the runtime is
  released, then the package needs to be added as an extra packge
  to package-notes.txt)

In cases where a separate branch is needed for RHEL, that is maintained
in a private fork of this repository.

## Creating a runtime for a new Fedora release

First make sure that the branches for new Fedora release are created in the
following components:

* [flatpaks/flatpak-runtime](https://src.fedoraproject.org/flatpaks/flatpak-runtime/branches) - this repository
* [flatpaks/flatpak-sdk](https://src.fedoraproject.org/flatpaks/flatpak-sdk/branches)
* [rpms/flatpak-runtime-config](https://src.fedoraproject.org/rpms/flatpak-runtime-config)

Once done, please do the following steps in this exact order:

1. Update `rpms/flatpak-runtime-config` package for a new Fedora release - i.e. [f35](https://src.fedoraproject.org/rpms/flatpak-runtime-config/c/c070b580e4ed7b200bcd26e6e055c2a2848c4962) and [f36](https://src.fedoraproject.org/rpms/flatpak-runtime-config/c/41b65b28446c382c193b4e2ff6d330e7b0f0b26b)
1. Create a new file under the data directory data/f41-live.packages (replace
   the f41 with the new release) and put the list of packages
   (`rpm -qa --qf "%{NAME}\n" | sort`) from a live Fedora Workstation media.
1. Replace all occurrences of an old Fedora release with the new one in `flatpaks/flatpak-runtime` - i.e. [f34 -> f35](https://src.fedoraproject.org/modules/flatpak-runtime/c/76972d6a76390f21e4e70fd960773e597d810de3) and [f35 -> f36](https://src.fedoraproject.org/modules/flatpak-runtime/c/ff05f48642694c1aaf70df1fdc0a5a6d8fb30939)
1. Bump the required freedesktop and GNOME Flatpak SDKs versions if required in
   `tools/generate-files.sh`
1. Run `make update`. In case of any problems you will need to update the
   `tools/resolve-files.py` to adapt it for new library versions and so on.
   Once the new runtime files are generated, consult the content of it and again
   modify `tools/resolve-files.py` to exclude any libraries, binaries or packages
   if needed.
1. Try to build the container locally with `flatpak-container local-build`
   to verify that the changes from previous step are working.
1. Commit the change and do the official build with `fedpkg module-build -w`
   followed by `fedpkg flatpak-build`
1. Update and build modules/flatpak-common - i.e. [f35 -> f36](https://src.fedoraproject.org/modules/flatpak-common/c/17aeabbc448e3805a85e2c9313d40c608bc2611b?branch=f36)
    and do an official build of with with `fedpkg module-build -w`. If you will
    hit any build problems you might want to try to build the module locally
    against the local packages with `flatpak-container build-module`. For that you
    have to [setup your environment](https://docs.fedoraproject.org/en-US/flatpak/troubleshooting/#_rebuilding_a_module_against_a_local_component)
1. Update modules/flatpak-sdk - i.e. [f35 -> f36](https://src.fedoraproject.org/modules/flatpak-sdk/c/83742941dc2b7e5c0cad78cb25c3ed9cc1b17d1a?branch=f36)
    and build it with `fedpkg flatpak-build` (no need to build a module for
    flatpak-sdk). On the other hand if you will need to make any changes to the
    flatpak-runtime definitions (to add more packages that are not pulled on
    x86_64 - i.e. [this change](https://src.fedoraproject.org/modules/flatpak-runtime/c/4737e749c62b19daf07366444517be9b98ff7ac9?branch=f36))
    then you will need to again do a module build of flatpak-runtime and once
    it's done, you can start a new `fedpkg flatpak-build` of flatpak-runtime
    and flatpak-sdk.
1. Create a bodhi update for the new runtime and SDK - i.e. [https://bodhi.fedoraproject.org/updates/FEDORA-FLATPAK-2022-16d56b1bde
1. Move all applications to the new runtime - i.e. [Evince Flatpak moving from f35 -> f36](https://src.fedoraproject.org/flatpaks/evince/c/7fccbf4bb8cea2d258226dfbe490327c59a44564?branch=stable)
    and build it with `fedpkg module-build -w` and `fedpkg flatpak-build`. Also
    it's a good time to update the `finish-args` from Flathub and update them
    in Fedora if needed. Also update the module packages with the changes from the new Fedora release - i.e. `fedmod rpm2flatpak --flatpak-common --force --flathub=gimp gimp`.
    You might find [the following howto useful](https://docs.fedoraproject.org/en-US/flatpak/tutorial/#_creating_application_yaml_and_container_yaml).
1. Create bodhi updates for moved applications
1. Switch to the new runtime for Anaconda - i.e. [f34 -> f35](https://pagure.io/pungi-fedora/c/d2e477b48368599834d6ec4adcc79f7115d98627?branch=main)
1. Once everything is moved, deprecate the old runtime and SDK - TBD
