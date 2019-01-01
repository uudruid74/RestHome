from os.path import dirname, basename, isfile
import glob
modules = glob.glob(dirname(__file__)+"/*.py")
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.startswith('device_virtual') and not f.endswith('__init__.py')]
__all__.append('device_virtual')

