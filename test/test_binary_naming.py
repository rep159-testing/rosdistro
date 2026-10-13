import os
import pytest
from rosdistro import get_index, get_distribution_file
from rosdistro.release_repository_specification import ReleaseRepositorySpecification
from rosdistro.distribution_file import DistributionFile


def test_release_repository_standard_naming():
    data = {
        'url': 'https://github.com/ros2-gbp/common_interfaces-release.git',
        'version': '5.9.2-2',
        'tags': {'release': 'release/rolling/{package}/{version}'},
        'packages': ['std_msgs']
    }
    repo = ReleaseRepositorySpecification('common_interfaces', data)
    repo.origin_distro = 'lyrical'
    
    assert repo.get_binary_package_name('std_msgs') == 'ros-lyrical-std-msgs'
    assert repo.target_distro_name == 'lyrical'


def test_release_repository_explicit_override():
    data = {
        'url': 'https://github.com/gazebosim/gz-cmake-release.git',
        'version': '5.1.1-2',
        'tags': {'release': 'gz-cmake5_{version}'},
        'packages': ['gz-cmake'],
        'binary_name': 'libgz-cmake5-dev'
    }
    repo = ReleaseRepositorySpecification('gz-cmake', data)
    repo.origin_distro = 'jetty'
    
    assert repo.get_binary_package_name('gz-cmake') == 'libgz-cmake5-dev'


def test_release_repository_custom_template():
    data = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_pkg'],
        'binary_prefix_template': 'custom-{distro}-{package}'
    }
    repo = ReleaseRepositorySpecification('custom_repo', data)
    repo.origin_distro = 'jazzy'
    
    assert repo.get_binary_package_name('my_pkg') == 'custom-jazzy-my-pkg'


def test_release_repository_empty_prefix_no_op():
    data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '10.5.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim10'],
        'binary_prefix': ''
    }
    repo = ReleaseRepositorySpecification('gz-sim', data)
    repo.origin_distro = 'jetty'
    
    assert repo.get_binary_package_name('gz_sim10') == 'gz-sim10'


def test_release_repository_sequential_regex_rules():
    data = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_special_package'],
        'binary_name_rules': [
            {'search': '^(.*)$', 'replace': 'vendor-{DISTRO}-\\1'}
        ]
    }
    repo = ReleaseRepositorySpecification('custom_repo', data)
    repo.origin_distro = 'iron'
    
    # Underscores in package name must be converted to dashes automatically
    assert repo.get_binary_package_name('my_special_package') == 'vendor-iron-my-special-package'


def test_release_repository_mandatory_underscore_sanitization():
    # 1. Rule that attempts to introduce underscores
    data_rules = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_pkg'],
        'binary_name_rules': [
            {'search': '^(.*)$', 'replace': 'vendor_{DISTRO}_\\1'}
        ]
    }
    repo_rules = ReleaseRepositorySpecification('custom_repo', data_rules)
    repo_rules.origin_distro = 'iron'
    assert repo_rules.get_binary_package_name('my_pkg') == 'vendor-iron-my-pkg'

    # 2. Explicit binary_name containing underscores
    data_explicit = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_pkg'],
        'binary_name': 'custom_vendor_pkg'
    }
    repo_explicit = ReleaseRepositorySpecification('custom_repo', data_explicit)
    assert repo_explicit.get_binary_package_name('my_pkg') == 'custom-vendor-pkg'

    # 3. Explicit binary_names mapping containing underscores
    data_dict = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_pkg'],
        'binary_names': {'my_pkg': 'dict_vendor_pkg'}
    }
    repo_dict = ReleaseRepositorySpecification('custom_repo', data_dict)
    assert repo_dict.get_binary_package_name('my_pkg') == 'dict-vendor-pkg'


def test_distribution_file_binary_naming():
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'repositories': {
            'ros_tutorials': {
                'release': {
                    'url': 'https://github.com/ros-gbp/ros_tutorials-release.git',
                    'version': '1.0.0-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['turtlesim']
                }
            }
        }
    }
    dist_file = DistributionFile('lyrical', dist_data)
    assert dist_file.get_binary_package_name('turtlesim') == 'ros-lyrical-turtlesim'
    assert dist_file.get_package_name_from_binary('ros-lyrical-turtlesim') == 'turtlesim'


def test_distribution_file_empty_binary_prefix():
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'binary_prefix': '',
        'release_platforms': {'ubuntu': ['noble']},
        'repositories': {
            'gz_cmake': {
                'release': {
                    'url': 'https://github.com/gazebosim/gz-cmake-release.git',
                    'version': '5.1.1-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['gz_cmake5']
                }
            }
        }
    }
    dist_file = DistributionFile('jetty', dist_data)
    assert dist_file.get_binary_package_name('gz_cmake5') == 'gz-cmake5'
    assert dist_file.get_package_name_from_binary('gz-cmake5') == 'gz_cmake5'


def test_distribution_file_reverse_lookup():
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'repositories': {
            'common_interfaces': {
                'release': {
                    'url': 'https://github.com/ros2-gbp/common_interfaces-release.git',
                    'version': '5.0.0-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['std_msgs', 'sensor_msgs']
                }
            }
        }
    }
    dist_file = DistributionFile('rolling', dist_data)
    assert dist_file.get_package_name_from_binary('ros-rolling-std-msgs') == 'std_msgs'
    assert dist_file.get_package_name_from_binary('ros-rolling-sensor-msgs') == 'sensor_msgs'
    assert dist_file.get_package_name_from_binary('ros-rolling-unknown') is None
