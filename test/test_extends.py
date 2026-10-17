import os
import pytest
from rosdistro import get_distribution_file, get_index, CircularInheritanceError
from . import path_to_url

FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files'))


def test_extends_parsing():
    url = path_to_url(os.path.join(FILES_DIR, 'index_extends.yaml'))
    index = get_index(url)

    # Test base distro loading
    base_dist = get_distribution_file(index, 'base')
    assert base_dist.version == 3
    assert 'bar_repo' in base_dist.repositories
    assert base_dist.repositories['bar_repo'].origin_distro == 'base'

    # Test derived distro loading and inheritance merging
    derived_dist = get_distribution_file(index, 'derived')
    assert derived_dist.version == 3

    # Check extends attributes are parsed correctly
    assert len(derived_dist.extends) == 1
    assert derived_dist.extends[0]['distro_name'] == 'base'
    assert derived_dist.extends[0]['extension_method'] == 'binary_import'

    # Check dependencies are parsed correctly
    assert len(derived_dist.dependencies) == 1
    assert derived_dist.dependencies[0]['rosdep_sources_list_urls'] == [
        'https://raw.githubusercontent.com/ros/rosdistro/master/rosdep/base.yaml'
    ]
    assert derived_dist.dependencies[0]['rosdep_minimum_target_platforms'] == [
        'ubuntu:noble'
    ]

    # Check repositories merged
    assert 'derived_repo' in derived_dist.repositories
    assert 'bar_repo' in derived_dist.repositories

    # Check metadata annotation
    assert derived_dist.repositories['derived_repo'].origin_distro == 'derived'
    assert derived_dist.repositories['derived_repo'].extension_method is None
    assert derived_dist.repositories['bar_repo'].origin_distro == 'base'
    assert derived_dist.repositories['bar_repo'].extension_method == 'binary_import'


def test_circular_extends():
    url = path_to_url(os.path.join(FILES_DIR, 'index_extends.yaml'))
    index = get_index(url)

    with pytest.raises(CircularInheritanceError) as excinfo:
        get_distribution_file(index, 'cyclic_a')
    assert "Circular inheritance detected" in str(excinfo.value)


def test_platform_compatibility_warning(caplog):
    url = path_to_url(os.path.join(FILES_DIR, 'index_extends.yaml'))
    index = get_index(url)

    get_distribution_file(index, 'derived_invalid_platform')
    assert "WARNING: Target platform 'ubuntu:quantal' specified in derived distribution is not supported by base distribution." in caplog.text


def test_multi_parent_precedence_and_collisions(caplog):
    url = path_to_url(os.path.join(FILES_DIR, 'index_extends.yaml'))
    index = get_index(url)

    child_dist = get_distribution_file(index, 'multi_parent_child')

    # Verify precedence: collision_repo release URL and version should match parent_a (0.1.0) because parent_a was declared first
    assert 'collision_repo' in child_dist.repositories
    assert child_dist.repositories['collision_repo'].release_repository.version == '0.1.0'

    # Verify collision warnings are logged for both repo and package
    assert "WARNING: Collision detected. Repository 'collision_repo' is defined in multiple parents ('parent_a' and 'parent_b'). Using definition from 'parent_a'." in caplog.text
    assert "WARNING: Collision detected. Package 'collision_pkg' is defined in multiple parents ('parent_a' and 'parent_b'). Using definition from 'parent_a'." in caplog.text

    # Verify metadata annotation: parent_a is binary_import, parent_b is source_rebuild
    # repo_a: imported from parent_a (binary_import) -> origin_distro remains parent_a
    assert child_dist.repositories['repo_a'].origin_distro == 'parent_a'
    assert child_dist.repositories['repo_a'].extension_method == 'binary_import'

    # repo_b: rebuilt from parent_b (source_rebuild) -> origin_distro becomes child (multi_parent_child)
    assert child_dist.repositories['repo_b'].origin_distro == 'multi_parent_child'
    assert child_dist.repositories['repo_b'].extension_method == 'source_rebuild'


def test_chained_cache_resolution():
    from rosdistro import get_distribution_cache
    url = path_to_url(os.path.join(FILES_DIR, 'index_extends.yaml'))
    index = get_index(url)

    # Load cache for 'derived' (which extends 'base')
    derived_cache = get_distribution_cache(index, 'derived')

    # Verify that the cache merged both distribution files in memory
    assert 'derived_repo' in derived_cache.distribution_file.repositories
    assert 'bar_repo' in derived_cache.distribution_file.repositories

    # Verify that the package XMLs from both caches are available
    assert 'derived_repo' in derived_cache.release_package_xmls
    assert 'bar_repo' in derived_cache.release_package_xmls

    assert "<name>derived_repo</name>" in derived_cache.release_package_xmls['derived_repo']
    assert "<name>bar_repo</name>" in derived_cache.release_package_xmls['bar_repo']


def test_binary_import_override_forbidden():
    from rosdistro.distribution_file import DistributionFile
    base_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'repositories': {
            'core_repo': {
                'release': {
                    'packages': ['core_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/ros-gbp/core-release.git',
                    'version': '1.0.0'
                }
            }
        }
    }
    child_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'extends': [{'distro_name': 'base', 'extension_method': 'binary_import'}],
        'repositories': {
            'core_repo': {
                'release': {
                    'packages': ['core_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/ros-gbp/core-release.git',
                    'version': '2.0.0'
                }
            }
        }
    }
    base_dist = DistributionFile('base', base_data)
    child_dist = DistributionFile('child', child_data)
    with pytest.raises(RuntimeError) as excinfo:
        child_dist.merge_extends(base_dist, 'binary_import')
    assert "violates ABI compatibility" in str(excinfo.value)


def test_source_rebuild_override_allowed():
    from rosdistro.distribution_file import DistributionFile
    base_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'repositories': {
            'core_repo': {
                'source': {
                    'type': 'git',
                    'url': 'https://github.com/ros/core.git',
                    'version': 'master'
                },
                'release': {
                    'packages': ['core_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/ros-gbp/core-release.git',
                    'version': '1.0.0'
                }
            }
        }
    }
    child_data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'extends': [{'distro_name': 'base', 'extension_method': 'source_rebuild'}],
        'repositories': {
            'core_repo': {
                'release': {
                    'packages': ['core_pkg'],
                    'tags': {'release': 'release/{package}/{version}'},
                    'url': 'https://github.com/ros-gbp/core-release.git',
                    'version': '2.0.0'
                }
            }
        }
    }
    base_dist = DistributionFile('base', base_data)
    child_dist = DistributionFile('child', child_data)
    child_dist.merge_extends(base_dist, 'source_rebuild')
    assert child_dist.repositories['core_repo'].release_repository.version == '2.0.0'
    assert child_dist.repositories['core_repo'].source_repository.url == 'https://github.com/ros/core.git'


def _release_stanza(package, version):
    return {
        'packages': [package],
        'tags': {'release': 'release/{package}/{version}'},
        'url': 'https://github.com/ros-gbp/%s-release.git' % package,
        'version': version,
    }


def _v3_distribution(repositories, extends=None):
    data = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['noble']},
        'repositories': repositories,
    }
    if extends:
        data['extends'] = [{'distro_name': extends, 'extension_method': 'binary_import'}]
    return data


def _base_with_ros_workspace():
    from rosdistro.distribution_file import DistributionFile
    return DistributionFile('base', _v3_distribution({
        'ros_workspace': {
            'source': {'type': 'git', 'url': 'https://github.com/ros2/ros_workspace.git', 'version': 'latest'},
            'release': _release_stanza('ros_workspace', '1.0.3-2'),
        },
        'core_repo': {'release': _release_stanza('core_pkg', '1.0.0-1')},
    }))


def test_binary_import_child_may_release_ros_workspace():
    # REP 159: the child's own ros_workspace provides setup files that source
    # the parents' setup files.
    from rosdistro.distribution_file import DistributionFile
    child = DistributionFile('child', _v3_distribution({
        'ros_workspace': {'release': _release_stanza('ros_workspace', '1.0.4-1')},
    }, extends='base'))
    child.merge_extends(_base_with_ros_workspace(), 'binary_import')
    workspace = child.repositories['ros_workspace']
    assert workspace.origin_distro == 'child'
    assert workspace.release_repository.version == '1.0.4-1'
    # the source entry the child's stanza lacks comes from the parent
    assert workspace.source_repository.url == 'https://github.com/ros2/ros_workspace.git'
    assert child.release_packages['ros_workspace'].repository_name == 'ros_workspace'
    # everything else is still the parent's binaries
    assert child.repositories['core_repo'].origin_distro == 'base'
    assert child.repositories['core_repo'].extension_method == 'binary_import'


def test_binary_import_ros_workspace_from_another_repository():
    from rosdistro.distribution_file import DistributionFile
    child = DistributionFile('child', _v3_distribution({
        'workspace': {'release': _release_stanza('ros_workspace', '1.0.4-1')},
    }, extends='base'))
    child.merge_extends(_base_with_ros_workspace(), 'binary_import')
    assert child.release_packages['ros_workspace'].repository_name == 'workspace'


def test_binary_import_other_overrides_still_forbidden():
    from rosdistro.distribution_file import DistributionFile
    child = DistributionFile('child', _v3_distribution({
        'ros_workspace': {'release': _release_stanza('ros_workspace', '1.0.4-1')},
        'core_repo': {'release': _release_stanza('core_pkg', '2.0.0-1')},
    }, extends='base'))
    with pytest.raises(RuntimeError, match="override repository 'core_repo'"):
        child.merge_extends(_base_with_ros_workspace(), 'binary_import')
