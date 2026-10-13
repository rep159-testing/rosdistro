import os
import pytest
from rosdistro import get_index, get_distribution_file
from rosdistro.release_repository_specification import ReleaseRepositorySpecification
from rosdistro.distribution_file import DistributionFile


def test_default_ros_template():
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


def test_empty_template_native_naming():
    data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '10.5.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim10'],
        'binary_template': '{{ package }}'
    }
    repo = ReleaseRepositorySpecification('gz-sim', data)
    repo.origin_distro = 'jetty'

    # {{ package }} must automatically have hyphens without needing package_hyphens
    assert repo.get_binary_package_name('gz_sim10') == 'gz-sim10'


def test_prefix_split_template():
    data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '10.5.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim'],
        'binary_template': '{{ package_parts[0] }}-{{ distro }}-{{ package_suffix }}'
    }
    repo = ReleaseRepositorySpecification('gz-sim', data)
    repo.origin_distro = 'lyrical'

    assert repo.get_binary_package_name('gz_sim') == 'gz-lyrical-sim'


def test_conditional_logic_in_jinja():
    template = "{% if package.startswith('gz') %}gz-{{ distro }}-{{ package_suffix }}{% else %}ros-{{ distro }}-{{ package_hyphens }}{% endif %}"
    
    gz_data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '10.5.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim'],
        'binary_template': template
    }
    gz_repo = ReleaseRepositorySpecification('gz-sim', gz_data)
    gz_repo.origin_distro = 'lyrical'
    assert gz_repo.get_binary_package_name('gz_sim') == 'gz-lyrical-sim'

    ros_data = {
        'url': 'https://github.com/ros-gbp/ros_tutorials-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['turtlesim'],
        'binary_template': template
    }
    ros_repo = ReleaseRepositorySpecification('ros_tutorials', ros_data)
    ros_repo.origin_distro = 'lyrical'
    assert ros_repo.get_binary_package_name('turtlesim') == 'ros-lyrical-turtlesim'


def test_explicit_binary_name_override():
    data = {
        'url': 'https://github.com/gazebosim/gz-cmake-release.git',
        'version': '5.1.1-2',
        'tags': {'release': 'gz-cmake5_{version}'},
        'packages': ['gz-cmake'],
        'binary_name': 'libgz-cmake5-dev',
        'binary_template': 'ros-{{ distro }}-{{ package_hyphens }}'
    }
    repo = ReleaseRepositorySpecification('gz-cmake', data)
    repo.origin_distro = 'jetty'

    # binary_name takes precedence over template
    assert repo.get_binary_package_name('gz-cmake') == 'libgz-cmake5-dev'


def test_multi_package_binary_names_override():
    data = {
        'url': 'https://github.com/ros2-gbp/common_interfaces-release.git',
        'version': '5.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['std_msgs', 'sensor_msgs', 'action_msgs'],
        'binary_names': {
            'std_msgs': 'libros-std-messages',
            'sensor_msgs': 'libros-sensor-messages'
        }
    }
    repo = ReleaseRepositorySpecification('common_interfaces', data)
    repo.origin_distro = 'jazzy'

    assert repo.get_binary_package_name('std_msgs') == 'libros-std-messages'
    assert repo.get_binary_package_name('sensor_msgs') == 'libros-sensor-messages'
    assert repo.get_binary_package_name('action_msgs') == 'ros-jazzy-action-msgs'


def test_distribution_file_jinja_templating_and_reverse_lookup():
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'binary_template': '{{ package_parts[0] }}-{{ distro }}-{{ package_suffix }}',
        'repositories': {
            'gz_sim': {
                'release': {
                    'url': 'https://github.com/gazebosim/gz-sim-release.git',
                    'version': '10.5.0-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['gz_sim']
                }
            },
            'ros_tutorials': {
                'release': {
                    'url': 'https://github.com/ros-gbp/ros_tutorials-release.git',
                    'version': '1.0.0-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['turtlesim'],
                    'binary_name': 'special-turtlesim-bin'
                }
            }
        }
    }
    dist_file = DistributionFile('lyrical', dist_data)
    assert dist_file.get_binary_package_name('gz_sim') == 'gz-lyrical-sim'
    assert dist_file.get_binary_package_name('turtlesim') == 'special-turtlesim-bin'

    # Reverse Lookup
    assert dist_file.get_package_name_from_binary('gz-lyrical-sim') == 'gz_sim'
    assert dist_file.get_package_name_from_binary('special-turtlesim-bin') == 'turtlesim'
    assert dist_file.get_package_name_from_binary('unknown-pkg') is None


def test_jinja_mandatory_underscore_sanitization():
    # 1. Template containing literal underscores
    data_template = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_pkg'],
        'binary_template': 'vendor_{{ distro }}_{{ package }}'
    }
    repo_template = ReleaseRepositorySpecification('custom_repo', data_template)
    repo_template.origin_distro = 'iron'
    assert repo_template.get_binary_package_name('my_pkg') == 'vendor-iron-my-pkg'

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
