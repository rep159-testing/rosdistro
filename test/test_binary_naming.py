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


def test_release_repository_prefix_rule():
    data = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_pkg'],
        'binary_rule': {
            'search': '^',
            'replace': 'custom-{distro}-'
        }
    }
    repo = ReleaseRepositorySpecification('custom_repo', data)
    repo.origin_distro = 'jazzy'
    
    assert repo.get_binary_package_name('my_pkg') == 'custom-jazzy-my-pkg'


def test_release_repository_exact_rename_rule():
    data = {
        'url': 'https://github.com/gazebosim/gz-cmake-release.git',
        'version': '5.1.1-2',
        'tags': {'release': 'gz-cmake5_{version}'},
        'packages': ['gz-cmake'],
        'binary_rule': {
            'search': '^gz-cmake$',
            'replace': 'libgz-cmake5-dev'
        }
    }
    repo = ReleaseRepositorySpecification('gz-cmake', data)
    repo.origin_distro = 'jetty'
    
    assert repo.get_binary_package_name('gz-cmake') == 'libgz-cmake5-dev'


def test_release_repository_empty_prefix_no_op_rule():
    data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '10.5.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim10'],
        'binary_rule': {
            'search': '^',
            'replace': ''
        }
    }
    repo = ReleaseRepositorySpecification('gz-sim', data)
    repo.origin_distro = 'jetty'
    
    # Preserves native package name without prepending 'ros-jetty-'
    assert repo.get_binary_package_name('gz_sim10') == 'gz-sim10'


def test_release_repository_capture_groups_rule():
    data = {
        'url': 'https://github.com/ros2-gbp/navigation2-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['nav2_bringup'],
        'binary_rule': {
            'search': '^nav2-(.*)$',
            'replace': 'acme-{DISTRO}-navigation-\\1'
        }
    }
    repo = ReleaseRepositorySpecification('navigation2', data)
    repo.origin_distro = 'iron'
    
    assert repo.get_binary_package_name('nav2_bringup') == 'acme-iron-navigation-bringup'


def test_release_repository_mandatory_underscore_sanitization():
    # Rule that introduces literal underscores in the replacement string
    data_rules = {
        'url': 'https://github.com/custom/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['my_special_package'],
        'binary_rule': {
            'search': '^',
            'replace': 'vendor_{DISTRO}_'
        }
    }
    repo_rules = ReleaseRepositorySpecification('custom_repo', data_rules)
    repo_rules.origin_distro = 'iron'
    
    # Both replacement string and package name underscores must be sanitized to dashes
    assert repo_rules.get_binary_package_name('my_special_package') == 'vendor-iron-my-special-package'


def test_distribution_file_binary_naming_default():
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


def test_distribution_file_global_binary_rule():
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'binary_rule': {
            'search': '^',
            'replace': 'custom-{DISTRO}-'
        },
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
    assert dist_file.get_binary_package_name('turtlesim') == 'custom-lyrical-turtlesim'
    assert dist_file.get_package_name_from_binary('custom-lyrical-turtlesim') == 'turtlesim'


def test_distribution_file_repo_override_rule():
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'binary_rule': {
            'search': '^',
            'replace': 'vendor-{DISTRO}-'
        },
        'release_platforms': {'ubuntu': ['noble']},
        'repositories': {
            'gz_cmake': {
                'release': {
                    'url': 'https://github.com/gazebosim/gz-cmake-release.git',
                    'version': '5.1.1-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['gz_cmake5'],
                    'binary_rule': {
                        'search': '^gz-cmake5$',
                        'replace': 'libgz-cmake5-dev'
                    }
                }
            },
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
    dist_file = DistributionFile('jetty', dist_data)
    # Repo override takes precedence
    assert dist_file.get_binary_package_name('gz_cmake5') == 'libgz-cmake5-dev'
    assert dist_file.get_package_name_from_binary('libgz-cmake5-dev') == 'gz_cmake5'

    # Fallback to distribution rule
    assert dist_file.get_binary_package_name('turtlesim') == 'vendor-jetty-turtlesim'
    assert dist_file.get_package_name_from_binary('vendor-jetty-turtlesim') == 'turtlesim'


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
