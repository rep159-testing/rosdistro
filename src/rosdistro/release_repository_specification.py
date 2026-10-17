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

import re

from .repository_specification import RepositorySpecification


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

        self.binary_rule = data.get('binary_rule', None) if isinstance(data, dict) else None
        self.install_rule = data.get('install_rule', None) if isinstance(data, dict) else None

        # for backward compatibility only
        self.release_repository = self

    @property
    def target_distro_name(self):
        origin_distro = getattr(self, 'origin_distro', None)
        extension_method = getattr(self, 'extension_method', None)
        if extension_method == 'binary_import' and origin_distro:
            return origin_distro
        return origin_distro or getattr(self, 'distro_name', None)

    def get_install_prefix(self, pkg_name=None):
        distro_name = self.target_distro_name or ''
        clean_distro = distro_name.replace('_', '-')
        clean_pkg = (pkg_name or self.name).replace('_', '-')
        origin_distro = getattr(self, 'origin_distro', None) or distro_name
        clean_origin = origin_distro.replace('_', '-')

        rule = getattr(self, 'install_rule', None)
        if rule:
            var_context = {
                'DISTRO': clean_distro,
                'distro': clean_distro,
                'PACKAGE': clean_pkg,
                'package': clean_pkg,
                'ORIGIN_DISTRO': clean_origin,
                'origin_distro': clean_origin,
            }
            if isinstance(rule, str):
                res = rule
                for k, v in var_context.items():
                    res = res.replace('{%s}' % k, v).replace('$%s' % k, v)
                return res
            elif isinstance(rule, dict) and 'search' in rule and 'replace' in rule:
                search_pattern = rule['search']
                replace_pattern = rule['replace']
                for k, v in var_context.items():
                    replace_pattern = replace_pattern.replace('{%s}' % k, v).replace('$%s' % k, v)
                return re.sub(search_pattern, replace_pattern, clean_pkg)

        if clean_distro:
            return '/opt/ros/%s' % clean_distro
        return '/usr'

    def get_binary_package_name(self, pkg_name, os_name=None):
        distro_name = self.target_distro_name or ''
        clean_distro = distro_name.replace('_', '-')
        clean_pkg = pkg_name.replace('_', '-')
        origin_distro = getattr(self, 'origin_distro', None) or distro_name
        clean_origin = origin_distro.replace('_', '-')

        rule = getattr(self, 'binary_rule', None)
        if rule and isinstance(rule, dict) and 'search' in rule and 'replace' in rule:
            var_context = {
                'DISTRO': clean_distro,
                'distro': clean_distro,
                'PACKAGE': clean_pkg,
                'package': clean_pkg,
                'ORIGIN_DISTRO': clean_origin,
                'origin_distro': clean_origin,
            }
            search_pattern = rule['search']
            replace_pattern = rule['replace']
            for k, v in var_context.items():
                replace_pattern = replace_pattern.replace('{%s}' % k, v).replace('$%s' % k, v)
            result = re.sub(search_pattern, replace_pattern, clean_pkg)
            return result.replace('_', '-')

        # Default Standard ROS convention
        if clean_distro:
            return 'ros-%s-%s' % (clean_distro, clean_pkg)
        return clean_pkg

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
        if self.binary_rule is not None:
            data['binary_rule'] = self.binary_rule
        if self.install_rule is not None:
            data['install_rule'] = self.install_rule
        return data
