'''Set all paths. This module prefers the new project layout (params/, meshes/).
It falls back to data/ if the old layout is present.'''

from os import path

this_file_dir = path.dirname(path.abspath(__file__))

BASE_DIR = path.abspath(path.join(this_file_dir, '..'))
RESULTS_DIR = path.join(BASE_DIR, 'results')

# Prefer the new params/ directory, but fall back to data/ for compatibility
if path.isdir(path.join(BASE_DIR, 'params')):
    PARAMS_DIR = path.join(BASE_DIR, 'params')
else:
    PARAMS_DIR = path.join(BASE_DIR, 'data')

PARAMETER_FILE = path.join(PARAMS_DIR, 'parameter.json')
PARAMETER_FILE_SI = path.join(PARAMS_DIR, 'parameter_si.json')
TEMP_DIR = path.join(PARAMS_DIR, 'temp')
DATA_DIR = PARAMS_DIR

# Meshes directory (new in the refactor)
MESHES_DIR = path.join(BASE_DIR, 'meshes')

print('Projekt Hauptverzeichnis:', BASE_DIR)
