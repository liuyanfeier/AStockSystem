"""Frozen adapter dispatch; historical evidence never adopts today's pins."""
from __future__ import annotations
import builtins
import types
from pathlib import Path
from astock.phase1.core import file_hash, require, strict_json

V1_REGISTRY_SHA = "09c8b5f8afe9201b797e5df6ab239836740c8cef43aaa97ae592c6825e255500"


def v1_registry(root):
    p = root / 'config/phase1/frozen-v1.json'
    require(file_hash(p) == V1_REGISTRY_SHA, 'FROZEN_VERSION_REGISTRY_CHANGED')
    v = strict_json(p.read_bytes())
    for name, checksum in v['pins'].items():
        require(file_hash(root / v['archive'] / name) == checksum, 'FROZEN_ADAPTER_CHANGED')
    return v


def validate(root, pinned):
    from astock.phase1 import acquisition
    if pinned == v1_registry(root)['pins']:
        return 'V1'
    if pinned == acquisition.pins(root):
        return 'V2'
    require(pinned == v1_registry(root)['pins'], 'UNREGISTERED_TRANSFORM_VERSION')
    return 'V1'


def adapters(root, pinned):
    if validate(root, pinned) == 'V2':
        from astock.phase1 import contracts, domains
        return contracts, domains
    v = v1_registry(root)
    package = types.ModuleType('frozen_phase1_v1')
    package.PROTOCOL = v['protocol']
    loaded = {}
    def load(name):
        if name in loaded: return loaded[name]
        module = types.ModuleType('frozen_phase1_v1.' + name)
        loaded[name] = module
        setattr(package, name, module)
        path = root / v['archive'] / 'src/astock/phase1' / (name + '.py')
        env = dict(vars(builtins))
        def importer(module_name, globals=None, locals=None, fromlist=(), level=0):
            if module_name == 'astock.phase1':
                for item in fromlist:
                    if item != 'PROTOCOL': load(item)
                return package
            if module_name.startswith('astock.phase1.'):
                return load(module_name.split('.')[-1])
            return builtins.__import__(module_name, globals, locals, fromlist, level)
        env['__import__'] = importer
        module.__dict__.update(__builtins__=env, __file__=str(path))
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
        return module
    # The unchanged v1 catalog is explicitly pinned as well.
    require(file_hash(root / 'config/phase1/contracts-v1.yaml') == v['pins']['config/phase1/contracts-v1.yaml'], 'V1_CATALOG_UNAVAILABLE')
    return load('contracts'), load('domains')
