import pytest
from rosdistro.release_repository_specification import ReleaseRepositorySpecification
from rosdistro.distribution_file import DistributionFile


def test_default_standard_ros_prefix():
    data = {
        'url': 'https://github.com/ros2-gbp/common_interfaces-release.git',
        'version': '5.9.2-2',
        'tags': {'release': 'release/rolling/{package}/{version}'},
        'packages': ['std_msgs']
    }
    repo = ReleaseRepositorySpecification('common_interfaces', data)
    repo.origin_distro = 'jazzy'

    assert repo.get_install_prefix('std_msgs') == '/opt/ros/jazzy'


def test_custom_vendor_install_prefix_regex():
    data = {
        'url': 'https://github.com/acme/teleop-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['teleop_keyboard'],
        'install_rule': {
            'search': '^.*$',
            'replace': '/opt/acme/{distro}'
        }
    }
    repo = ReleaseRepositorySpecification('teleop', data)
    repo.origin_distro = 'jazzy'

    assert repo.get_install_prefix('teleop_keyboard') == '/opt/acme/jazzy'


def test_custom_vendor_install_prefix_template_string():
    data = {
        'url': 'https://github.com/vendor/repo-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['vendor_tool'],
        'install_rule': '/opt/vendor/{distro}'
    }
    repo = ReleaseRepositorySpecification('vendor_repo', data)
    repo.origin_distro = 'rolling'

    assert repo.get_install_prefix('vendor_tool') == '/opt/vendor/rolling'


def test_isolated_per_package_install_prefix_prepend():
    data = {
        'url': 'https://github.com/custom/pkg-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['custom_driver'],
        'install_rule': {
            'search': '^',
            'replace': '/opt/ros/{distro}/'
        }
    }
    repo = ReleaseRepositorySpecification('custom_driver', data)
    repo.origin_distro = 'upstream'

    assert repo.get_install_prefix('custom_driver') == '/opt/ros/upstream/custom-driver'


def test_isolated_per_package_install_prefix_template():
    data = {
        'url': 'https://github.com/custom/pkg-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['custom_driver'],
        'install_rule': {
            'search': '^.*$',
            'replace': '/opt/ros/{distro}/{package}'
        }
    }
    repo = ReleaseRepositorySpecification('custom_driver', data)
    repo.origin_distro = 'upstream'

    assert repo.get_install_prefix('custom_driver') == '/opt/ros/upstream/custom-driver'


def test_group_capture_install_prefix():
    data = {
        'url': 'https://github.com/gazebosim/gz-sim-release.git',
        'version': '1.0.0-1',
        'tags': {'release': '{package}/{version}'},
        'packages': ['gz_sim'],
        'install_rule': {
            'search': '^gz-(.*)$',
            'replace': '/opt/osrf/{distro}/\\1'
        }
    }
    repo = ReleaseRepositorySpecification('gz_sim', data)
    repo.origin_distro = 'harmonic'

    assert repo.get_install_prefix('gz-sim') == '/opt/osrf/harmonic/sim'


def test_distribution_level_install_prefix_propagation():
    dist_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['resolute']},
        'install_rule': {
            'search': '^.*$',
            'replace': '/opt/custom/{distro}'
        },
        'repositories': {
            'pkg_a': {
                'release': {
                    'url': 'https://github.com/org/pkg_a-release.git',
                    'version': '1.0.0-1',
                    'tags': {'release': '{package}/{version}'},
                    'packages': ['pkg_a']
                }
            }
        }
    }
    dist_file = DistributionFile('custom_distro', dist_data)
    assert dist_file.get_install_prefix() == '/opt/custom/custom-distro'
    assert dist_file.get_install_prefix('pkg_a') == '/opt/custom/custom-distro'
    assert dist_file.repositories['pkg_a'].release_repository.get_install_prefix('pkg_a') == '/opt/custom/custom-distro'
