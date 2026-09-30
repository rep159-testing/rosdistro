import os

import pytest
import yaml

from rosdistro import get_cached_distribution
from rosdistro import get_index

from . import path_to_url

FILES_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'files'))
# Holds the distribution `base` together with its cache (files/extends/).
PARENT_INDEX_URL = path_to_url(os.path.join(FILES_DIR, 'index_extends.yaml'))


def _write_child_index(tmp_path, extends):
    """Write an index holding only `child`, a v3 distribution with `extends`."""
    distribution = {
        'type': 'distribution',
        'version': 3,
        'release_platforms': {'ubuntu': ['precise']},
        'extends': extends,
        'repositories': {
            'child_repo': {
                'release': {
                    'tags': {'release': 'release/child/{package}/{version}'},
                    'url': 'https://github.com/example-release/child_repo.git',
                    'version': '1.0.0',
                },
            },
        },
    }
    cache = {
        'type': 'cache',
        'version': 2,
        'name': 'child',
        'distribution_file': distribution,
        'release_package_xmls': {
            'child_repo': (
                '<package><name>child_repo</name><version>1.0.0</version>'
                '<description>child_repo</description>'
                '<maintainer email="test@example.com">Test</maintainer>'
                '<license>BSD</license></package>'),
        },
    }
    index = {
        'type': 'index',
        'version': 4,
        'distributions': {
            'child': {
                'distribution': ['child.yaml'],
                'distribution_cache': 'child-cache.yaml',
            },
        },
    }
    for file_name, data in (
            ('child.yaml', distribution),
            ('child-cache.yaml', cache),
            ('index.yaml', index)):
        with open(str(tmp_path / file_name), 'w') as f:
            yaml.safe_dump(data, f)
    return get_index(path_to_url(str(tmp_path / 'index.yaml')))


def test_parent_cache_comes_from_the_extends_index_url(tmp_path):
    index = _write_child_index(tmp_path, [{
        'distro_name': 'base',
        'index_url': PARENT_INDEX_URL,
        'extension_method': 'binary_import'}])
    dist = get_cached_distribution(index, 'child')
    assert 'bar_repo' in dist.release_packages
    assert dist.repositories['bar_repo'].origin_distro == 'base'
    assert dist.repositories['bar_repo'].extension_method == 'binary_import'
    assert '<name>bar_repo</name>' in dist.get_release_package_xml('bar_repo')


def test_unreachable_parent_index_raises(tmp_path):
    missing = path_to_url(str(tmp_path / 'missing' / 'index.yaml'))
    index = _write_child_index(tmp_path, [{
        'distro_name': 'base',
        'index_url': missing,
        'extension_method': 'binary_import'}])
    with pytest.raises(RuntimeError, match="'base', which 'child' extends"):
        get_cached_distribution(index, 'child')


def test_parent_missing_from_the_same_index_raises(tmp_path):
    index = _write_child_index(tmp_path, [{
        'distro_name': 'base',
        'extension_method': 'binary_import'}])
    with pytest.raises(RuntimeError, match="'base', which 'child' extends"):
        get_cached_distribution(index, 'child')
