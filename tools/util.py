import collections.abc
from dataclasses import dataclass
from functools import cached_property
import gzip
import hashlib
from pathlib import Path
import pickle
from typing import Iterable, List, Mapping
import rpm
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import xml.sax

import config

XDG_CACHE_HOME = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")

_log_name = None

def set_log_name(name):
    global _log_name
    _log_name = name

def warn(msg):
    print("{}: \033[31m{}\033[39m".format(_log_name, msg), file=sys.stderr)

def error(msg):
    print("{}: \033[31m{}\033[39m".format(_log_name, msg), file=sys.stderr)
    sys.exit(1)

def start(msg):
    print("{}: \033[90m{} ... \033[39m".format(_log_name, msg), file=sys.stderr, end="")
    sys.stderr.flush()

def done():
    print("\033[90mdone\033[39m", file=sys.stderr)

def package_cmp(p1, p2):
    n1, e1, v1, r1, a1 = p1
    n2, e2, v2, r2, a2 = p2

    if a1 == 'i686' and a2 != 'i686':
        return 1
    if a1 != 'i686' and a2 == 'i686':
        return -1

    if n1.startswith('compat-') and not n2.startswith('compat-'):
        return 1
    elif n2.startswith('compat-') and not n1.startswith('compat-'):
        return -1

    if n1.startswith('python2-') and n2.startswith('python3-'):
        return 1
    elif n1.startswith('python3-') and n2.startswith('python2-'):
        return -1

    if (n1.startswith('jack-audio-connection-kit')
            and n2.startswith('pipewire-jack-audio-connection-kit')):
        return 1
    elif (n1.startswith('pipewire-jack-audio-connection-kit')
            and n2.startswith('jack-audio-connection-kit')):
        return -1

    if n1 < n2:
        return -1
    elif n1 > n2:
        return 1

    if e1 is None:
        e1 = '0'
    if e2 is None:
        e2 = '0'

    return - rpm.labelCompare((e1, v1, r1), (e2, v2, r2))


def depchase_output(args, arch="amd64", platform_only=False):
    repo_args = config.REPO_ARGS
    if not platform_only:
        repo_args += config.SDK_EXTRA_REPO_ARGS

    return subprocess.check_output(
        ['flatpak-container-depchase'] + repo_args + ["--arch", arch] + args,
        encoding='utf-8'
    )


@dataclass
class RepoInfo():
    name: str
    metadata_path: Path

    @cached_property
    def repomd_contents(self) -> bytes:
        with open(self.metadata_path / "repomd.xml", "rb") as f:
            return f.read()

    @staticmethod
    def fetch(platform_only=False):
        repo_infos: List[RepoInfo] = []

        for line in depchase_output(["fetch-metadata", "--print-location"],
                                    platform_only=platform_only).strip().split("\n"):
            name, metadata_path = [p.strip() for p in line.split()]
            repo_infos.append(RepoInfo(name, Path(metadata_path)))

        return repo_infos

    def get_metadata_file(self, type_):
        root = ET.fromstring(self.repomd_contents)
        ns = {'repo': 'http://linux.duke.edu/metadata/repo'}
        location_element = root.find(f"./repo:data[@type='{type_}']/repo:location", ns)
        assert location_element is not None
        location = location_element.attrib['href']
        path = self.metadata_path.parent / location
        if Path(os.path.commonpath([path, self.metadata_path])) != self.metadata_path:
            raise RuntimeError(f"{self.metadata_path}: {type} file is outside of repository")

        return path


class FilesMapHandler(xml.sax.ContentHandler):
    def __init__(self, cb):
        self.cb = cb
        self.package_info = None
        self.name = None
        self.arch = None
        self.epoch = None
        self.version = None
        self.release = None
        self.file = None
        self.package_info = None

    def startElement(self, name, attrs):
        if name == 'package':
            self.name = attrs['name']
            self.arch = attrs['arch']
        elif name == 'version':
            if self.name is not None:
                self.epoch = attrs['epoch']
                self.version = attrs['ver']
                self.release = attrs['rel']
        elif name == 'file':
            self.file = ''

    def endElement(self, name):
        if name == 'package':
            self.package_info = None
        elif name == 'file':
            if self.package_info is None:
                self.package_info = (self.name, self.epoch, self.version, self.release, self.arch)
            self.cb(self.package_info, self.file)
            self.file = None

    def characters(self, content):
        if self.file is not None:
            self.file += content


def foreach_file(repo_info: RepoInfo, cb):
    start(f"Scanning files for {repo_info.name}")
    filelists_path = repo_info.get_metadata_file("filelists")

    handler = FilesMapHandler(cb)
    with gzip.open(filelists_path, 'rb') as f:
        xml.sax.parse(f, handler)

    done()


class PackageMapHandler(xml.sax.ContentHandler):
    def __init__(self, cb):
        self.cb = cb
        self.name = None
        self.sourcerpm = None
        self.chars = None

    def startElement(self, name, attrs):
        if name == 'package':
            pass
        elif name in ('name', 'rpm:sourcerpm'):
            self.chars = ''

    def endElement(self, name):
        if name == 'package':
            self.cb(self.name, self.sourcerpm)
            self.name = None
            self.sourcerpm = None
        elif name == 'name':
            self.name = self.chars
            self.chars = None
        elif name == 'rpm:sourcerpm':
            self.sourcerpm = self.chars
            self.chars = None

    def characters(self, content):
        if self.chars is not None:
            self.chars += content


def foreach_package(repo_info: RepoInfo, cb):
    start(f"Scanning files for {repo_info.name}")

    primary_path = repo_info.get_metadata_file("primary")
    handler = PackageMapHandler(cb)
    with gzip.open(primary_path, 'rb') as f:
        xml.sax.parse(f, handler)

    done()


def _get_repo_cacheable(repo_info, name, generate):
    repo_hash = hashlib.sha256(repo_info.repomd_contents).hexdigest()

    cache_path = os.path.join('out', name + "-" + repo_info.name + ".gz")

    try:
        with gzip.open(cache_path, 'rb') as f:
            old_repo_hash = f.read(64).decode('utf-8')
            if old_repo_hash == repo_hash:
                start("Reading " + name)
                data = pickle.load(f)
                done()

                return data
    except FileNotFoundError:
        pass

    data = generate(repo_info)

    start("Writing " + name)
    with gzip.open(cache_path, 'wb') as f:
        f.write(repo_hash.encode('utf-8'))
        pickle.dump(data, f)
    done()

    return data


class UnionMapping(collections.abc.Mapping):
    def __init__(self, children: Iterable[Mapping]):
        self.children = children

    def __contains__(self, key):
        for child in self.children:
            if key in child:
                return True

        return False

    def __getitem__(self, key):
        for child in self.children:
            try:
                return child[key]
            except KeyError:
                pass

        raise KeyError(key)

    def __iter__(self):
        return (i for c in self.children for i in c)

    def __len__(self):
        # This is only approximate
        return sum(len(child) for child in self.children)


def get_repo_map(name, generate, platform_only=False):
    repos = RepoInfo.fetch(platform_only=platform_only)
    child_maps = [_get_repo_cacheable(r, name, generate) for r in repos]

    return UnionMapping(child_maps)
