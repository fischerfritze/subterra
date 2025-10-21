'''Set all paths. This module prefers the new project layout (params/, meshes/).
It falls back to data/ if the old layout is present.'''

import os

this_file_dir = os.path.dirname(os.path.abspath(__file__))

BASE_DIR = os.path.abspath(os.path.join(this_file_dir, '..'))
RESULTS_DIR = os.path.join(BASE_DIR, 'results')

# Prefer the new params/ directory, but fall back to data/ for compatibility
if os.path.isdir(os.path.join(BASE_DIR, 'params')):
	PARAMS_DIR = os.path.join(BASE_DIR, 'params')
else:
	PARAMS_DIR = os.path.join(BASE_DIR, 'data')

PARAMETER_FILE = os.path.join(PARAMS_DIR, 'parameter.json')
PARAMETER_FILE_SI = os.path.join(PARAMS_DIR, 'parameter_si.json')
TEMP_DIR = os.path.join(PARAMS_DIR, 'temp')
DATA_DIR = PARAMS_DIR

# Meshes directory (new in the refactor)
MESHES_DIR = os.path.join(BASE_DIR, 'meshes')

print('Projekt Hauptverzeichnis:', BASE_DIR)