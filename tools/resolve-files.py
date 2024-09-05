#!/usr/bin/python3

import os
import re
import sys

import util
from util import start, done, warn

if len(sys.argv) != 2:
    print("Usage: resolve-files.py INFILE", file=sys.stderr)
    sys.exit(1)

inpath = sys.argv[1]
if not inpath.endswith('.files'):
    print("INFILE must have .files suffix", file=sys.stderr)
    sys.exit(1)

util.set_log_name(inpath)

base_path = inpath[:-len('.files')]
is_platform = "-Platform" in base_path
is_sdk = "-Sdk" in base_path

############################################################

ignore = set()
rename = dict()

# Use this for individual utilities absent or unsupported in Fedora;
# to exclude entire packages, use *_package_ignore_patterns below
bin_ignore = [
    # /usr/share/doc/aspell/aspell-import in Fedora
    'aspell-import',

    # compatibility perl script in zenity for something quite old, not packaged in fedora
    'gdialog',

    # glibc-utils not packaged in Fedora
    'nscd', 'sln', 'trace',

    # GPG test program (https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=tree;f=tests)
    'gpgscm',

    # An implementation of tar for cross-platform compatibility, disabled in gnupg2.spec
    'gpgtar',

    # gnutls utlilties not packaged in Fedora
    'srptool',

    # groff contrib utilities not packaged in Fedora
    'groffer', 'roff2dvi', 'roff2html', 'roff2pdf', 'roff2ps', 'roff2text', 'roff2x',

    # gstreamer1 utilities not packaged in Fedora
    'gst-tester-1.0', 'playout',

    # kf5-*/phonon-qt5 in <=39, kf6-*/phonon-qt6 in >=40
    'kde-geo-uri-handler', 'kwalletd5', 'kwalletd6', 'kwallet-query', 'phononsettings',

    # libjpeg-turbo utilities not packaged in Fedora
    'tjbench',

    # libselinux utilities not packaged in Fedora
    'compute_av', 'compute_create', 'compute_member', 'compute_relabel', 'getfilecon',
    'getpidcon', 'getseuser', 'policyvers', 'selinux_check_securetty_context',
    'setfilecon', 'togglesebool',

    # removed from npth-devel
    'npth-config',

    # nss tools unsupported or unpackaged in Fedora
    'hw-support', 'nss', 'pwdecrypt', 'shlibsign', 'signtool', 'symkeyutil', 'validation',

    # Versioned python-3.10 binaries
    'pydoc3.10', 'python3.10', 'python3.10-config', 'python3.10m',  'python3.10m-config', '2to3-3.10',
    'easy_install-3.10', 'pip3.10', 'pyvenv-3.10',

    # Versioned python-3.11 binaries
    'pydoc3.11', 'python3.11', 'python3.11-config', 'python3.11m',  'python3.11m-config', '2to3-3.11',
    'easy_install-3.11', 'pip3.11', 'pyvenv-3.11',

    # removed from python-3.13
    '2to3',

    # nettle utilities not currently packaged in fedora
    # (https://src.fedoraproject.org/rpms/nettle/c/2ec204e2de17006b566c9ff7d90ec65ca1680ed5?branch=master)
    'nettle-hash', 'nettle-lfib-stream', 'nettle-pbkdf2', 'pkcs1-conv', 'sexp-conv',

    # krb5 sample utilities not packaged in Fedora
    'gss-client', 'gss-server', 'krb5-send-pr', 'sim_client', 'sim_server',
    'uuclient', 'uuserver',

    # Debian login/passwd/util-linux
    'expiry', 'faillog', 'logoutd', 'mkfs.bfs',

    # OpenEmbedded uses Debian's ca-certificates, Fedora is different
    'update-ca-certificates',

    # specific to community SDKs
    'freedesktop-sdk-stripper',
]
ignore.update('/usr/bin/' + x for x in bin_ignore)

# development tools in the freedesktop runtime
platform_bin_ignore = [
    'fftw-wisdom', 'fftw-wisdom-to-conf',
    'make',
    'm4',
    'orcc',
    'yelp-build', 'yelp-check', 'yelp-new',
]
if is_platform:
    ignore.update('/usr/bin/' + x for x in platform_bin_ignore)

bin_rename = {
    # bzip2
    'bzfless': 'bzless',

    # clang
    'clang-17': 'clang',

    # cups-client
    'lpr': 'lpr.cups',

    # GIO/GTK module file generators
    'gdk-pixbuf-query-loaders': 'gdk-pixbuf-query-loaders-64',
    'gio-querymodules': 'gio-querymodules-64',
    'gtk-query-immodules-2.0': 'gtk-query-immodules-2.0-64',
    'gtk-query-immodules-3.0': 'gtk-query-immodules-3.0-64',

    # glslang
    'glslang': 'glslangValidator',

    # libselinux-utils
    'getconlist': 'selinuxconlist',
    'getdefaultcon': 'selinuxdefcon',

    # perl
    'perl5.38.0': 'perl',

    # vala
#    'vala-0.56': 'vala-0.56',
#    'vala-gen-introspect-0.56': 'vala-gen-introspect-0.56',
#    'valac-0.56': 'valac-0.56',
#    'vapigen-0.56': 'vapigen-0.56',
}
rename.update({'/usr/bin/' + k: '/usr/bin/' + v for k, v in bin_rename.items()})

lib_ignore = [
    # Symlink created in freedesktop.org flatpak runtime, not standard
    'libEGL_indirect.so.0',
    'load-p11-kit-trust.so',

    # From AppArmor; Fedora/RHEL use SELinux instead
    'libapparmor.so', 'libapparmor.so.1',

    # binutils internal libraries
    'libbfd-2.42.so', 'libopcodes-2.42.so', 'libgprofng.so', 'libgprofng.so.0',

    # Trimmed from gettext(-devel)
    'libgettextlib.so', 'libgettextsrc.so', 'libtextstyle.so', 'libtextstyle.so.0',

    # binutils-gprofng private libraries
    'libgprofng.so', 'libgprofng.so.0',

    # Part of glibc
    'libc_malloc_debug.so', 'libssp.so.0',

    # glslang is built as static libraries only
    'libHLSL.so.12', 'libHLSL.so', 'libSPIRV.so.12', 'libSPIRV.so',
    'libSPVRemapper.so.12', 'libSPVRemapper.so', 'libglslang.so.12', 'libglslang.so',

    # Disabled in libunwind
    'libunwind-ptrace.so', 'libunwind-ptrace.so.0',
    'libunwind-setjmp.so', 'libunwind-setjmp.so.0',
]
ignore.update('/usr/lib64/' + x for x in lib_ignore)

lib_rename = {
    # Older in Fedora
#    'libabigail.so.4': 'libabigail.so.3',
    'libpkgconf.so.5': 'libpkgconf.so.4',
#    'libsframe.so.1': 'libsframe.so.0',
#    'libtiff.so.6': 'libtiff.so.5',
#    'libtiffxx.so.6': 'libtiffxx.so.5',

    # Newer in Fedora
#    'libaom.so.3': 'libaom.so.3',
    'libappstream.so.4': 'libappstream.so.5',
#    'libasan.so.8': 'libasan.so.8',
#    'libavcodec.so.60': 'libavcodec.so.60',
#    'libavdevice.so.60': 'libavdevice.so.60',
#    'libavfilter.so.9': 'libavfilter.so.9',
#    'libavformat.so.60': 'libavformat.so.60',
#    'libavutil.so.58': 'libavutil.so.58',
    'libavif.so.15': 'libavif.so.16',
    'libclang-cpp.so.17': 'libclang-cpp.so.18.1',
    'libclang.so.17': 'libclang.so.18.1',
    'libdav1d.so.6': 'libdav1d.so.7',
#    'libffi.so.8': 'libffi.so.8',
#    'libFLAC++.so.10': 'libFLAC++.so.10',
#    'libFLAC.so.12': 'libFLAC.so.12',
    'libgettextlib-0.22.so': 'libgettextlib-0.22.5.so',
    'libgettextsrc-0.22.so': 'libgettextsrc-0.22.5.so',
#    'libgnutlsxx.so.30': 'libgnutlsxx.so.30',
#    'libkadm5clnt_mit.so.12': 'libkadm5clnt_mit.so.12',
#    'libkadm5srv_mit.so.12': 'libkadm5srv_mit.so.12',
#    'libkdb5.so.10': 'libkdb5.so.10',
    'libLLVM-17.so': 'libLLVM-18.so',
    'libLLVMSPIRVLib.so.17': 'libLLVMSPIRVLib.so.18.1',
    'libLTO.so.17': 'libLTO.so.18.1',
#    'libmozjs-115.so': 'libmozjs-115.so',
    'libnsl.so.1': 'libnsl.so.3',
    'libonig.so.4': 'libonig.so.5',
    'libopenh264.so.6': 'libopenh264.so.7',
#    'libpcre2-posix.so.3': 'libpcre2-posix.so.3',
    'libpython3.11.so.1.0': 'libpython3.13.so.1.0',
    'libpython3.11.so': 'libpython3.13.so',
    'libRemarks.so.17': 'libRemarks.so.18.1',
#    'libsepol.so.2': 'libsepol.so.2',
#    'libswscale.so.7': 'libswscale.so.7',
#    'libunistring.so.5': 'libunistring.so.5',
#    'libvala-0.56.so': 'libvala-0.56.so',
#    'libvala-0.56.so.0': 'libvala-0.56.so.0',
    'libverto.so.0': 'libverto.so.1',
    'libvpx.so.8': 'libvpx.so.9',
    'libwebrtc_audio_processing.so': 'libwebrtc-audio-processing-1.so',
    'libwebrtc_audio_processing.so.1': 'libwebrtc-audio-processing-1.so.3',
    'libwget.so.1': 'libwget.so.2',
    'libZXing.so.1': 'libZXing.so.3',

    # Replaced by libxcrypt in Fedora
    'libcrypt.so.1': 'libcrypt.so.2',

    # Compat symlink in gcr
    'libgcr-3.so.1': 'libgcr-ui-3.so.1',

    # ncurses is built with a single tinfo library for both narrow and wide
    'libtinfow.so': 'libtinfo.so',
    'libtinfow.so.6': 'libtinfo.so.6',

    # named differently when built with autotools vs cmake
    'libSDL2_image-2.0.so': 'libSDL2_image.so',
    'libSDL2_mixer-2.0.so': 'libSDL2_mixer.so',
    'libSDL2_net-2.0.so': 'libSDL2_net.so',

    # Fedora arch-handling
    'ld-linux.so.2': 'ld-linux-x86-64.so.2',
}
rename.update({'/usr/lib64/' + k: '/usr/lib64/' + v for k, v in lib_rename.items()})

gcc_libs = [
    'libasan.so', 'libatomic.so', 'libgcc_s.so', 'libgfortran.so', 'libgomp.so',
    'libhwasan.so', 'libitm.so', 'liblsan.so', 'libobjc.so', 'libquadmath.so',
    'libstdc++.so', 'libtsan.so', 'libubsan.so'
]
rename.update({'/usr/lib64/' + x: '/usr/lib/gcc/x86_64-redhat-linux/14/' + x for x in gcc_libs})

for old in ['libasm-0.189.so', 'libdw-0.189.so', 'libelf-0.189.so', 'libdebuginfod-0.189.so']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('-0.189', '-0.191')

# Fedora may have newer icu
for old in ['libicudata.so.73', 'libicui18n.so.73', 'libicuio.so.73', 'libicutest.so.73',
            'libicutu.so.73', 'libicuuc.so.73']:
    rename['/usr/lib64/' + old] = '/usr/lib64/' + old.replace('so.73', 'so.74')

include_rename = {
    'asoundlib.h': 'alsa/asoundlib.h',
    'assuan.h': 'libassuan2/assuan.h',
}
rename.update({ '/usr/include/' + k: '/usr/include/' + v for k, v in include_rename.items() })

nspr_include = [
    'nspr.h', 'plarena.h', 'plarenas.h', 'plbase64.h', 'plerror.h', 'plgetopt.h', 'plhash.h',
    'plstr.h', 'pratom.h', 'prbit.h', 'prclist.h', 'prcmon.h', 'prcountr.h', 'prcpucfg.h',
    'prcvar.h', 'prdtoa.h', 'prenv.h', 'prerr.h', 'prerror.h', 'prinet.h', 'prinit.h',
    'prinrval.h', 'prio.h', 'pripcsem.h', 'private/pprio.h', 'private/pprthred.h', 'private/prpriv.h',
    'prlink.h', 'prlock.h', 'prlog.h', 'prlong.h', 'prmem.h', 'prmon.h', 'prmwait.h', 'prnetdb.h',
    'prolock.h', 'prpdce.h', 'prprf.h', 'prproces.h', 'prrng.h', 'prrwlock.h', 'prshm.h', 'prshma.h',
    'prsystem.h', 'prthread.h', 'prtime.h', 'prtpool.h', 'prtrace.h', 'prtypes.h', 'prvrsion.h',
    'prwin16.h', 'stropts.h', 'obsolete/pralarm.h', 'obsolete/probslet.h', 'obsolete/protypes.h', 'obsolete/prsem.h'
]
rename.update({'/usr/include/' + x: '/usr/include/nspr4/' + x for x in nspr_include})

# pipewire jack libraries are installed in a non-standard path
jack_libraries = [
    'libjack.so', 'libjacknet.so', 'libjackserver.so'
]
rename.update({'/usr/lib64/' + x: '/usr/lib64/pipewire-0.3/jack/' + x for x in jack_libraries})

# These plugins in the freedesktop runtime pull in gstreamer-plugins-bad-free-extras, which
# in turn pulls in a lot more dependencies. If they are useful, they should be moved
# to gstreamer-plugins-bad-free.
gstreamer_plugins_ignore = {
    'libgstaom.so', 'libgstcurl.so', 'libgstdecklink.so', 'libgstladspa.so',
    'libgstopenal.so', 'libgstva.so'
}
ignore.update('/usr/lib64/gstreamer-1.0/' + x for x in gstreamer_plugins_ignore)

pc_ignore = {
    # Trimmed from xorg-x11-proto-devel (xorgproto)
    'applewmproto.pc',

    # From AppArmor; Fedora/RHEL use SELinux instead
    'libapparmor.pc',

    # https://github.com/ostroproject/ostro-os/blob/master/meta/recipes-support/libassuan/libassuan/libassuan-add-pkgconfig-support.patch
    'libassuan.pc',

    # http://cgit.openembedded.org/openembedded-core/tree/meta/recipes-support/libgcrypt/files/0001-Add-and-use-pkg-config-for-libgcrypt-instead-of-conf.patch
    'libgcrypt.pc',

    # Disabled in libunwind
    'libunwind-setjmp.pc',

    # ncurses is built with a single tinfo library for both narrow and wide
    'tinfow.pc'
}
ignore.update('/usr/lib64/pkgconfig/' + x for x in pc_ignore)
ignore.update('/usr/share/pkgconfig/' + x for x in pc_ignore)

pc_rename = {
#    'libvala-0.56.pc': 'libvala-0.56.pc',
#    'mozjs-115.pc': 'mozjs-115.pc',
    'python-3.11.pc': 'python-3.13.pc',
    'python-3.11-embed.pc': 'python-3.13-embed.pc',
#    'vapigen-0.56.pc': 'vapigen-0.56.pc',
    'webrtc-audio-processing.pc': 'webrtc-audio-processing-1.pc',
}
rename.update({'/usr/lib64/pkgconfig/' + k: '/usr/lib64/pkgconfig/' + v for k, v in pc_rename.items()})
rename.update({'/usr/share/pkgconfig/' + k: '/usr/share/pkgconfig/' + v for k, v in pc_rename.items()})

hunspell_ignore = {
    # regionless symlinks, correctly detected by full xx_XX name
    'gl.aff', 'gl.dic', 'is.aff', 'is.dic', 'te.aff', 'te.dic', 'tr.aff', 'tr.dic',
}
ignore.update('/usr/share/hunspell/' + x for x in hunspell_ignore)

hyph_ignore = {
    # regionless symlinks, correctly detected by full xx_XX name
    'hyph_de.dic', 'hyph_gl.dic', 'hyph_is.dic', 'hyph_te.dic',
}
ignore.update('/usr/share/hyphen/' + x for x in hyph_ignore)

ignore_patterns = [
    # Flatpak runtime has a versioned gawk-5.0.1
    r'/usr/bin/gawk-.*',

    # Architecture specific aliases for gcc, binutils, etc
    r'^/usr/bin/x86_64-unknown-linux-.*',

    # Trimmed from xorg-x11-proto-devel (xorgproto)
    r'/usr/include/X11/extensions/applewm.*',

    # From NSPR, intentionally not installed on Fedora
    r'/usr/include/md/.*',

    # From AppArmor; Fedora/RHEL use SELinux instead
    r'/usr/include/sys/apparmor.*',

    # Trimmed from gettext-devel
    r'/usr/include/textstyle.*',

    # Trimmed from ncurses-devel
    r'/usr/include/nc_tparm.h',
    r'/usr/include/tic.h',

    # Headers moved in webrtc-audio-processing-1.3
    r'/usr/include/webrtc_audio_processing/.*',

    # Trimmed from Fedora perl packages, or pull -devel into platform
    r'/usr/lib64/perl5.*/.packlist',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/MakeMaker/Locale\.pm',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/MakeMaker/version\.pm',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/PL2Bat\.pm',
    r'/usr/lib64/perl5/[\d.]+/ExtUtils/typemap',
    r'/usr/lib64/perl5/[\d.]+/.*/File/Spec/VMS\.pm',
    r'/usr/lib64/perl5/[\d.]+/pod/.*',

    # Pulls in a conflicting compatibiliy version of python3-cython
    r'/usr/lib64/python[\d.]+/site-packages/Cython/Includes/Deprecated/.*',
    r'/usr/lib64/python[\d.]+/site-packages/Cython/(Plex/Timing|Plex/Traditional)\.py',
    r'/usr/lib64/python[\d.]+/site-packages/Cython/Utility/Capsule\.c',

    # Qt private API headers, micro version will not always align
    r'/usr/include/Qt.*/[\d.]+/Qt.*',

    # Monolithic driver (individual driver symlinks are detected)
    r'^/usr/lib64/GL/default/lib/dri/libgallium_.*.so',
    r'^/usr/lib64/GL/default/lib/vdpau/libvdpau_gallium.so.*',
    # Trace library
    r'^/usr/lib64/GL/default/lib/vdpau/libvdpau_trace.so.*',
    # Unversioned symlinks are not packaged
    r'^/usr/lib64/GL/default/lib/vdpau/libvdpau_.*.so$',

    # Windows binaries?
    r'/usr/lib64/python[\d.]+/site-packages/setuptools/.*.exe',

    # differences in pip packaging - unbundling
    r'^/usr/lib64/python[\d.]+/site-packages/pip/_internal/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/pip/_vendor/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/pkg_resources/_vendor/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/setuptools/_vendor/.*',

    # Let the python files pull in the packages, avoid versioned directory names
    r'^/usr/lib64/python[\d.]+/site-packages/[^/]*.dist-info/.*',
    r'^/usr/lib64/python[\d.]+/site-packages/[^/]*.egg-info.*',

    # fcitx
    r'/usr/lib64/libfcitx.*',

    # .install files litter the include directories of openembedded
    r'.*/\.install$',

    # .la files
    r'.*\.la$',

    # .pyc files shouldn't affect what is needed
    r'.*\.pyc$',

    # Font ID files for fontconfig
    r'/usr/share/fonts(|/.*)/.*\.uuid',

    # We build these into the gtk+ library
    r'^/usr/lib64/gtk-[^/]*/[^/]*/immodules/im-wayland.so',
    r'^/usr/lib64/gtk-[^/]*/[^/]*/immodules/im-waylandgtk.so',

    # provided by both dvtm and ncurses-term; only the latter is wanted
    r'^/usr/share/terminfo/d/dvtm.*',
]
ignore_compiled = [re.compile(x) for x in ignore_patterns]

rename_patterns = [
    (r'^/usr/include/c\+\+/[\d\.]*/x86_64-unknown-linux-gnu/(.*)', r'/usr/include/c++/14/x86_64-redhat-linux/\1'),
    (r'^/usr/include/c\+\+/[\d\.]*/(.*)', r'/usr/include/c++/14/\1'),
    (r'^/usr/include/(libav.*)', r'/usr/include/ffmpeg/\1'),
    (r'^/usr/include/(libsw.*)', r'/usr/include/ffmpeg/\1'),
#    (r'^/usr/include/mozjs-115/(.*)', r'/usr/include/mozjs-115/\1'),
    (r'^/usr/include/nss/(.*)', r'/usr/include/nss3/\1'),
    (r'^/usr/include/(proxy.h)', r'/usr/include/libproxy/\1'),
    (r'^/usr/include/python3.11/(.*)', r'/usr/include/python3.13/\1'),
    (r'^/usr/include/ruby-[\d\.]*/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-[\d\.]*/x86_64-linux/ruby/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/ruby-[\d\.]*/(.*)', r'/usr/include/ruby/\1'),
    (r'^/usr/include/sysprof-[\d]+/(.*)', r'/usr/include/sysprof-6/\1'),
    (r'^/usr/lib64/GL/default/lib/(OpenCL/vendors/.*)', r'/etc/\1'),
    (r'^/usr/lib64/GL/default/lib/(vulkan/icd.d/.*)', r'/usr/share/\1'),
    (r'^/usr/lib64/GL/default/lib/(.*)', r'/usr/lib64/\1'),
    (r'^/usr/lib64/GL/default/share/clc/(.*)', r'/usr/lib64/clc/\1'),
    (r'^/usr/lib64/GL/default/share/(.*)', r'/usr/share/\1'),
    (r'^/usr/lib64/gstreamer-1.0/(gst-.*)', r'/usr/libexec/gstreamer-1.0/\1'),
    (r'^/usr/lib64/perl5/site_perl/[\d.]+/x86_64-linux/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/site_perl/[\d.]+/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/vendor_perl/[\d.]+/x86_64-linux/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/vendor_perl/[\d.]+/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/[\d.]+/x86_64-linux/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/perl5/[\d.]+/(.*)', r'/usr/lib64/perl5/\1'),
    (r'^/usr/lib64/pkgconfig/(.*proto.pc)', r'/usr/share/pkgconfig/\1'),
    (r'^/usr/lib64/pkgconfig/ruby-[\d\.]*.pc', r'/usr/lib64/pkgconfig/ruby.pc'),
    (r'^/usr/lib64/python3.11/(site-packages/_dbus.*).cpython-311-.*', r'/usr/lib64/python3.13/\1.so'),
    (r'^/usr/lib64/python3.11/(.*).cpython-311-(.*)', r'/usr/lib64/python3.13/\1.cpython-313-\2'),
    (r'^/usr/lib64/python3.11/(.*)', r'/usr/lib64/python3.13/\1'),
    (r'^/usr/lib64/(v4l[12].*.so)', r'/usr/lib64/libv4l/\1'),
    (r'^/usr/share/fonts/cantarell/(Cantarell-VF.otf)', r'/usr/share/fonts/abattis-cantarell-vf-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuMath.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSansMono.*)', r'/usr/share/fonts/dejavu-sans-mono-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSans.*)', r'/usr/share/fonts/dejavu-sans-fonts/\1'),
    (r'^/usr/share/fonts/dejavu/(DejaVuSerif.*)', r'/usr/share/fonts/dejavu-serif-fonts/\1'),
    (r'^/usr/share/fonts/google-crosextra-caladea/(Caladea.*)', r'/usr/share/fonts/google-crosextra-caladea-fonts/\1'),
    (r'^/usr/share/fonts/google-crosextra-carlito/(Carlito.*)', r'/usr/share/fonts/google-carlito-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationMono.*)', r'/usr/share/fonts/liberation-mono-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSans.*)', r'/usr/share/fonts/liberation-sans-fonts/\1'),
    (r'^/usr/share/fonts/liberation-fonts/(LiberationSerif.*)', r'/usr/share/fonts/liberation-serif-fonts/\1'),
    (r'^/usr/share/fonts/noto-emoji/(NotoColorEmoji.*)', r'/usr/share/fonts/google-noto-color-emoji-fonts/\1'),
]
rename_compiled = [(re.compile(a), b) for a, b in rename_patterns]

global_package_ignore_patterns = [
    # The Fedora packages of fcitx pull in qt4. While would be nice to match the upstream
    # runtime in including fcitx for full compatibility when the host is using fcitx,
    # it doesn't seem worth the increase in runtime size.
    '^fcitx-.*$',

    # Should be installed on the host instead
    '^arptables-legacy$',
    '^audispd-plugins$',
    '^audit$',
    "^authselect$",
    '^avahi$',
    '^avahi-autoipd$',
    '^avahi-dnsconfd$',
    '^avahi-gobject.*',
    '^avahi-ui.*',
    '^cryptsetup.*$',
    "^cups-ipptool$",
    "^cups-printerapp$",
    '^dbus$',
    '^dbus-broker$',
    '^dbus-daemon$',
    '^dbus-x11$',
    '^device-mapper.*$',
    '^dvb-tools$',
    '^ebtables-legacy$',
    '^fuse$',
    '^ibus$',
    '^ibus-setup$',
    '^integritysetup$',
    '^iptables.*$',
    '^jack-audio-connection-kit$',
    '^kbd$',
    '^kbd-legacy$',
    '^kbd-misc$',
    '^kmod$',
    '^kmod-devel$',
    '^krb5-server$',
    '^libaio.*',
    '^libdaemon.*',
    '^libmnl.*',
    '^libnftnl.*',
    '^lvm2.*$',
    '^nscd$',
    '^openresolv$',
    '^pam$',
    '^passwd$',
    '^pipewire$',
    '^pipewire-pulse$',
    '^pipewire-v4l2$',
    '^pulseaudio$',
    '^shadow-utils-subid$',
    '^switcheroo-control$',
    '^systemd$',
    '^systemd-container$',
    '^systemd-networkd$',
    '^systemd-resolved$',
    '^systemd-standalone-repart$',
    '^systemd-udev$',
    '^tracker$',
    '^uuidd$',
    '^v4l-utils$',
    '^v4l-utils-devel-tools$',
    '^veritysetup$',
    '^xdg-dbus-proxy$',
    '^xdg-desktop-portal$',
    '^xdg-desktop-portal-devel$',

    # unnecessary utilities, or unwanted due to dependencies;
    # if any of these need to be made available in SDK for compatibility,
    # move them to platform_package_ignore_patterns[] below
    "^aom$",
    "^aspell.*",
    '^avahi-tools$',
    '^avahi-ui-tools$',
    "^bsd(cat|cpio|tar|unzip)$",  # libarchive
    "^cyrus-sasl$",
    "^dav1d$",
    '^enchant2-nuspell$',
    '^fido2-tools$',
    '^gamemode.*',
    '^gcab$',
    '^gdbm$',
    '^giflib-utils$',
    '^gitk$',
    '^glibc-utils$',
    '^gnutls-utils$',
    '^gstreamer1-plugins-base-tools$',
    '^gtksourceview5-tests$',
    '^idn2$',
    '^itcl$',
    '^itcl-devel$',
    '^itk$',
    '^itk-devel$',
    r'^kf[\d]+-sonnet-aspell$',
    '^lcms2-utils$',
    '^libbpf.*',
    '^libcap-ng-utils$',
    '^libeconf-utils$',
    '^libei-utils$',
    '^libevdev-utils$',
    '^libselinux-utils$',
    '^libsepol-utils$',
    '^libsndfile-utils$',
    '^libtasn1-tools$',
    '^libtiff-tools$',
    '^libxkbcommon-utils$',
    '^libvpx-utils$',
    '^mythes.*',  # used only by libreoffice
    '^nuspell*',
    '^openjpeg-tools$',
    '^openssh$',
    '^openssl-pkcs11$',  # replaced by pkcs11-provider
    '^pciutils$',
    '^pcre-tools$',
    '^pcre2-tools$',
    '^pipewire-utils$',
    '^plocate$',
    '^psl$',
    '^psl-make-dafsa$',
    '^pulseaudio-utils$',
    '^qrencode$',
    '^qv4l2$',  # requires qt5
    '^speex-tools$',
    '^sqlite$',
    '^sqlite-analyzer$',
    '^svt-av1$',
    '^tcl-thread$',
    '^tcl-thread-devel$',
    '^texinfo-tex$',  # requires texlive
    '^xxhash$',

    # file conflicts
    '^coreutils-single$',  # conflicts with coreutils
    r'^openssl1\.1-devel$',  # conflicts with openssl-devel from openssl 3.0
    '^golang-github-cespare-xxhash$', # conflicts with xxhash
    '^golang-github-google-martian$', # conflicts with libproxy-bin
    '^golang-github-xo-terminfo$',  # conflicts on /usr/bin/infocmp with ncurses
    '^elfutils-debuginfod$',  # we don't need debuginfod server
]

global_package_ignore_compiled = [re.compile(p) for p in global_package_ignore_patterns]

platform_package_ignore_patterns = [
    "^.*-devel$",
    "^appstream-compose",
    "^libappstream-glib-builder$", # may not need in the sdk either
    "^gcc-gdb-plugin$",  # pulls in gcc
    '^gperf$',
    "^gtk-doc$",
    "^gtk4-devel-tools$",
    "^icu$",  # may not need in the sdk either
    '^itstool$',
    '^krb5-pkinit$',
    '^krb5-workstation$',
    '^librsvg2-tools$',
    '^llvm$',
    '^llvm-test$',  # pulls in gcc and binutils
    '^openssl$',
    '^perl',  # all perl components should be only in sdk
    '^python3-attrs$',
    '^python3-jinja2$',
    '^python3-test$',
    '^sqlite$',
    '^xcb-proto$',
    '^xmltoman$',
]
platform_package_ignore_compiled = [re.compile(p) for p in platform_package_ignore_patterns]


# We need to look up a lot of file dependencies. dnf/libsolv is not fast at doing
# this (at least when we look up files one-by-one) so we create a hash table that
# maps from *all* files in the distribution to the "best" package that provides
# the file. To further speed this up, we pickle the result and store it, and only
# recreate it when the DNF metadata changes. We gzip the pickle to save space
# (70M instead of 700M), this slows things down by about 2 seconds.
#
def make_files_map(repo_info):
    files_map = {}

    def cb(package_info, f):
        old = files_map.get(f)
        if old is None or util.package_cmp(package_info, old) < 0:
            files_map[f] = package_info

    util.foreach_file(repo_info, cb)

    start("Finalizing files map")
    for k in files_map:
        files_map[k] = files_map[k][0]
    done()

    return files_map

def get_files_map(platform_only=False):
    return util.get_repo_map('files-map', make_files_map, platform_only=platform_only)

start("Reading file list")

to_resolve = []
with open(inpath) as f:
    for line in f:
        r = line.rstrip()
        if r.startswith('/usr/lib/x86_64-linux-gnu/'):
            r = '/usr/lib64/' + r[len('/usr/lib/x86_64-linux-gnu/'):]
        elif r.startswith('/usr/lib/'):
            r = '/usr/lib64/' + r[len('/usr/lib/'):]
        to_resolve.append(r)

to_resolve.sort()

done()

files_map = get_files_map(platform_only=is_platform)
found_packages = set()

start("Resolving files to packages")

matched_file = open(base_path + '.matched', 'w')
unmatched_file = open(base_path + '.unmatched', 'w')
unmatched_count = 0

for r in to_resolve:
    if r in ignore:
        continue

    skip = False
    for p in ignore_compiled:
        if p.match(r) is not None:
            skip = True
    if skip:
        continue

    if r in rename:
        r = rename[r]

    for p, replacement in rename_compiled:
        if p.match(r) is not None:
            r = p.sub(replacement, r)

    if os.path.dirname(r) == '/usr/lib64':
        search = [r, '/lib64/' + os.path.basename(r)]
    elif r.startswith('/usr/lib64') and r.find('/site-packages/') > 0:
        # Python packages can be either in /usr/lib64 or /usr/lib
        search = [r, '/usr/lib/' + r[len('/usr/lib64/'):]]
    elif r.startswith('/usr/lib64/perl5') > 0:
        # Perl packages can be either in privlib or archlib, and may be
        # packaged in vendorlib or vendorarch instead
        search = [r,
            '/usr/lib64/perl5/vendor_perl/' + r[len('/usr/lib64/perl5/'):],
            '/usr/share/perl5/vendor_perl/' + r[len('/usr/lib64/perl5/'):],
            '/usr/share/perl5/' + r[len('/usr/lib64/perl5/'):],
        ]
    elif r.startswith('/usr/bin/'):
        search = [r, '/bin/' + os.path.basename(r), '/usr/sbin/' + os.path.basename(r), '/sbin/' + os.path.basename(r)]
    else:
        search = [r]

    if r.startswith('/usr/lib64/libLLVM'):
        # freedesktop SDK builds "split" LLVM libraries
        found_packages.add('llvm-libs')
        continue

    for s in search:
        providing = files_map.get(s, None)
        if providing is not None:
            break
    else:
        providing = None

    if providing is None:
        print(r, file=unmatched_file)
        unmatched_count += 1
    else:
        # On Fedora glibc-headers-s390 and glibc-headers-x86_64 are no-arch
        # dependencies of glibc-devel required on the specific platform;
        # we just normalize to glibc-devel and let dependencies pull in the
        # appropriate glibc-headers package.
        if providing.startswith("glibc-headers-"):
            providing = "glibc-devel"

        if any(p.match(providing) is not None for p in global_package_ignore_compiled):
            continue

        if is_platform and any(p.match(providing) is not None for p in platform_package_ignore_compiled):
            continue

        found_packages.add(providing)
        print("{}: {}".format(r, providing), file=matched_file)

unmatched_file.close()
matched_file.close()

with open(base_path + '.packages', 'w') as f:
    for p in sorted(found_packages):
        print(p, file=f)

done()

if unmatched_count > 0:
    warn("{} unmatched files, see {}".format(unmatched_count, base_path + ".unmatched"))
