"""Plugin System - hot-reloadable plugins"""
import os
import json
import importlib.util
import time

class Plugin:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.module = None
        self.enabled = True
        self.loaded_at = None

    def load(self):
        spec = importlib.util.spec_from_file_location(self.name, self.path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.loaded_at = time.time()
        if hasattr(self.module, "on_load"):
            self.module.on_load()

    def execute(self, *args, **kwargs):
        if not self.module:
            self.load()
        if hasattr(self.module, "execute"):
            return self.module.execute(*args, **kwargs)
        raise Exception(f"Plugin {self.name} has no execute() function")

    def reload(self):
        self.load()

    def to_dict(self):
        return {
            "name": self.name,
            "enabled": self.enabled,
            "loaded": self.module is not None,
            "loaded_at": self.loaded_at,
            "path": self.path
        }

class PluginManager:
    def __init__(self, plugin_dir=None):
        self.plugin_dir = plugin_dir or os.path.expanduser("~/.ck-nexus/plugins")
        os.makedirs(self.plugin_dir, exist_ok=True)
        self.plugins = {}

    def discover(self):
        for item in os.listdir(self.plugin_dir):
            path = os.path.join(self.plugin_dir, item)
            if item.endswith(".py") and os.path.isfile(path):
                self.plugins[item[:-3]] = Plugin(item[:-3], path)
            elif os.path.isdir(path):
                init_path = os.path.join(path, "__init__.py")
                if os.path.exists(init_path):
                    self.plugins[item] = Plugin(item, init_path)
                main_path = os.path.join(path, f"{item}.py")
                if os.path.exists(main_path):
                    self.plugins[item] = Plugin(item, main_path)
        return list(self.plugins.keys())

    def load(self, name=None):
        if name:
            if name in self.plugins:
                self.plugins[name].load()
                return True
            return False
        for plugin in self.plugins.values():
            try:
                plugin.load()
            except Exception as e:
                print(f"Failed to load {plugin.name}: {e}")
        return True

    def reload(self, name=None):
        if name and name in self.plugins:
            self.plugins[name].reload()
            return True
        for plugin in self.plugins.values():
            try:
                plugin.reload()
            except:
                pass
        return True

    def execute(self, name, *args, **kwargs):
        if name not in self.plugins:
            raise Exception(f"Plugin {name} not found")
        return self.plugins[name].execute(*args, **kwargs)

    def list_all(self):
        return {name: p.to_dict() for name, p in self.plugins.items()}

    def install(self, name, code, description=""):
        plugin_dir = os.path.join(self.plugin_dir, name)
        os.makedirs(plugin_dir, exist_ok=True)
        with open(os.path.join(plugin_dir, "__init__.py"), "w") as f:
            f.write(code)
        meta = {"name": name, "description": description, "installed": time.time()}
        with open(os.path.join(plugin_dir, "plugin.json"), "w") as f:
            json.dump(meta, f, indent=2)
        self.plugins[name] = Plugin(name, os.path.join(plugin_dir, "__init__.py"))
        return True

    def uninstall(self, name):
        if name in self.plugins:
            del self.plugins[name]
        plugin_dir = os.path.join(self.plugin_dir, name)
        if os.path.exists(plugin_dir):
            import shutil
            shutil.rmtree(plugin_dir)
        return True
