#!/bin/bash
set -e

nvr=$(koji list-tagged --quiet --inherit --latest f41-build appstream-data|awk '{print $1}')
path=$(koji buildinfo $nvr | grep noarch.rpm | sed 's/\t.*$//')
url=$(echo $path | sed s@/mnt/koji/packages/@https://kojipkgs.fedoraproject.org/packages/@)

rpm=out/$(basename $path)

mkdir -p out
[ -e $rpm ] || curl $url > $rpm

tmpdir=$(mktemp -d)
cleanup() {
    rm -rf $tmpdir
}
trap cleanup EXIT

tmpxmldir=$tmpdir/usr/share/swcatalog/xml/
mkdir -p $tmpxmldir
rpm2cpio $rpm | ( cd $tmpdir && cpio -iv  './usr/share/swcatalog/xml/fedora.xml.gz' )
cp $tmpxmldir/fedora.xml.gz out/fedora-appstream.xml.gz

