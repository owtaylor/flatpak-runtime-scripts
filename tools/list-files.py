#!/usr/bin/python3

import os
import re
import sys

sdk = len(sys.argv) > 1 and sys.argv[1] == '--sdk'

def output_dir(d):
    if not os.path.isdir(d):
        return

    for f in sorted(os.listdir(d)):
        full = os.path.join(d, f)
        if not os.path.isdir(full):
            print(os.path.join(d, f))

def output_dir_recurse(d):
    for dirName, subdirs, files in os.walk(d):
        for f in sorted(files):
            print(os.path.join(dirName, f))

output_dir('/usr/bin')

python_dirs = []
for d in ['/usr/lib', '/usr/lib/x86_64-linux-gnu']:
    for f in os.listdir(d):
        full = os.path.join('/usr/lib', f)
        if (re.match(r'^.*\.so\.\d+$', f) is not None
                or re.match(r'^.*\.so$', f) is not None and not os.path.islink(full)):
            print(full)
        if (re.match('python[2-9]*', f)):
            python_dirs.append(os.path.join(full, 'site-packages'))

for d in python_dirs:
    output_dir_recurse(d)

output_dir_recurse('/usr/share/aclocal')
output_dir_recurse('/usr/share/cracklib')
output_dir_recurse('/usr/share/fonts')
output_dir_recurse('/usr/share/hunspell')
output_dir_recurse('/usr/share/hyphen')
output_dir_recurse('/usr/share/iso-codes')
output_dir_recurse('/usr/share/terminfo')
output_dir_recurse('/usr/share/themes')
output_dir_recurse('/usr/lib/perl5/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/alsa-lib/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/frei0r-1/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/GL/default/lib/dri/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/GL/default/lib/vdpau/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/GL/default/lib/vulkan/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0/2.10.0/loaders/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/gio/modules/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/gstreamer-1.0/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/ossl-modules/')
output_dir_recurse('/usr/lib/x86_64-linux-gnu/sasl2/')

for d in ('gtk-2.0', 'gtk-3.0', 'gtk-4.0'):
    try:
        for v in os.listdir(os.path.join('/usr/lib/x86_64-linux-gnu/', d)):
            output_dir_recurse(os.path.join('/usr/lib/x86_64-linux-gnu/', d, v, 'immodules'))
    except FileNotFoundError:
        pass

if sdk:
    output_dir_recurse('/usr/include')
    output_dir('/usr/lib/pkgconfig')
    output_dir('/usr/lib/x86_64-linux-gnu/pkgconfig/')
    output_dir('/usr/share/pkgconfig')

# import pkgutil
# for f in pkgutil.iter_modules():
#     try:
#         path = f[0].path
#         if path.find('site-packages') < 0:
#             continue
#     except AttributeError:
#         continue
#     if not(f[1].startswith('_')):
#         print(f, 'python3dist({})'.format(f[1]))

