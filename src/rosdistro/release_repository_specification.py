# Software License Agreement (BSD License)
#
# Copyright (c) 2013, Open Source Robotics Foundation, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Open Source Robotics Foundation, Inc. nor
#    the names of its contributors may be used to endorse or promote
#    products derived from this software without specific prior
#    written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import logging
import re
from .repository_specification import RepositorySpecification

logger = logging.getLogger('rosdistro')


def _expand_jinja_template(template_str, context):
    try:
        import jinja2
    except ImportError:
        logger.error("Jinja2 is required for binary name templating. Please install jinja2.")
        raise
    try:
        env = jinja2.Environment(autoescape=False, undefined=jinja2.StrictUndefined)
        template = env.from_string(template_str)
        return template.render(**context).strip()
    except Exception as e:
        logger.error("Failed to render Jinja template '%s' with context %s: %s" % (template_str, context, e))
        raise


class ReleaseRepositorySpecification(RepositorySpecification):

    def __init__(self, name, data):
        super(ReleaseRepositorySpecification, self).__init__(name, data)
        assert self.type in ('git', 'tar')

        self.tags = {}
        if self.version is not None:
            assert 'tags' in data
            assert 'release' in data['tags']
        if 'tags' in data:
            for tag_type in data['tags']:
                tag_data = data['tags'][tag_type]
                self.tags[tag_type] = str(tag_data)

        self.package_names = []
        if 'packages' in data and data['packages']:
            self.package_names = sorted(data['packages'])
        else:
            # no packages means a single package
            self.package_names = [self.name]

        # Support binary naming customization via Jinja template or direct naming
        self.binary_name = data.get('binary_name', None)
        self.binary_names = data.get('binary_names', None)
        self.binary_template = data.get('binary_template', None)
        self.binary_prefix = data.get('binary_prefix', None)

        # for backward compatibility only
        self.release_repository = self

    @property
    def target_distro_name(self):
        origin_distro = getattr(self, 'origin_distro', None)
        if getattr(self, 'extension_method', None) == 'source_rebuild':
            return origin_distro
        return origin_distro or getattr(self, 'distro_name', None)

    def get_binary_package_name(self, pkg_name, os_name=None):
        if hasattr(self, 'binary_names') and isinstance(self.binary_names, dict) and pkg_name in self.binary_names:
            return self.binary_names[pkg_name].replace('_', '-')
        if hasattr(self, 'binary_name') and self.binary_name:
            return self.binary_name.replace('_', '-')

        distro_name = self.target_distro_name or ''
        clean_distro = distro_name.replace('_', '-')
        clean_pkg = pkg_name.replace('_', '-')
        raw_pkg = pkg_name
        parts = [p for p in re.split(r'[-_]', pkg_name) if p]
        prefix_part = parts[0] if len(parts) > 1 else ''
        suffix_part = '-'.join(parts[1:]) if len(parts) > 1 else clean_pkg
        origin_distro = getattr(self, 'origin_distro', None) or distro_name
        clean_origin = origin_distro.replace('_', '-')

        context = {
            'package': clean_pkg,
            'package_raw': raw_pkg,
            'package_hyphens': clean_pkg,
            'package_underscores': pkg_name.replace('-', '_'),
            'package_parts': parts,
            'package_prefix': prefix_part,
            'package_suffix': suffix_part,
            'distro': clean_distro,
            'distro_raw': distro_name,
            'origin_distro': clean_origin,
            'origin_distro_raw': origin_distro,
            'DISTRO': clean_distro,
            'PACKAGE': clean_pkg,
            'ORIGIN_DISTRO': clean_origin,
        }

        template = getattr(self, 'binary_template', None)
        if template is None:
            prefix = getattr(self, 'binary_prefix', None)
            if prefix is not None:
                template = "%s{{ package_hyphens }}" % prefix
            elif clean_distro:
                template = "ros-{{ distro }}-{{ package_hyphens }}"
            else:
                template = "{{ package_hyphens }}"

        expanded = _expand_jinja_template(template, context)
        return expanded.replace('_', '-')

    def get_release_tag(self, pkg_name):
        data = {
            'package': pkg_name
        }
        if self.version:
            data['version'] = self.version
            data['upstream_version'] = self.version.split('-')[0]
        release_tag = self.tags['release']
        for k, v in data.items():
            release_tag = release_tag.replace('{%s}' % k, v)
        return release_tag

    def get_data(self):
        data = self._get_data(skip_git_type=True)
        if self.tags:
            data['tags'] = {}
            for tag in self.tags:
                data['tags'][tag] = str(self.tags[tag])
        if len(self.package_names) > 1 or (len(self.package_names) == 1 and self.package_names[0] != self.name):
            data['packages'] = sorted(self.package_names)
        if self.binary_name is not None:
            data['binary_name'] = self.binary_name
        if self.binary_names is not None:
            data['binary_names'] = self.binary_names
        if self.binary_template is not None:
            data['binary_template'] = self.binary_template
        if self.binary_prefix is not None:
            data['binary_prefix'] = self.binary_prefix
        return data

