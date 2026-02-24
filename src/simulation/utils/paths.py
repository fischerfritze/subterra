'''Set all paths.'''

from os import path

this_file_dir = path.dirname(path.abspath(__file__))

# repo root: .../src/simulation -> ../..
BASE_DIR = path.abspath(path.join(this_file_dir, '..', '..', '..'))
RESULTS_DIR = path.join(BASE_DIR, 'results')
PARAMS_DIR = path.join(BASE_DIR, 'params')
PARAMETER_FILE = path.join(PARAMS_DIR, 'parameter.json')
PARAMETER_FILE_SI = path.join(PARAMS_DIR, 'parameter_si.json')
TEMP_DIR = path.join(PARAMS_DIR, 'temp')
DATA_DIR = PARAMS_DIR
MESHES_DIR = path.join(BASE_DIR, 'meshes')

# Meshes directory (new in the refactor)
MESHES_DIR = path.join(BASE_DIR, 'meshes')

print('Projekt Hauptverzeichnis:', BASE_DIR)
