# SubTerra Docker Usage

## Build the Docker image

```bash
docker build -t subterra-calc -f src/simulation/Dockerfile .
```

## Run the calculation

You must mount your parameter file and results directory into the container. The calculation script expects the first argument to be the path to the parameter file, and the second (optional) argument to be the output `.h5` file path.

### Example: Run calculation with params and output file

```bash
docker run --rm \
  -v /absolute/path/to/params.json:/subterra/params.json \
  -v /absolute/path/to/results:/subterra/results \
  subterra-calc /subterra/params.json /subterra/results/output.h5
```

- `/absolute/path/to/params.json` is your parameter file on the host.
- `/absolute/path/to/results` is a directory on the host where results will be written.
- `/subterra/params.json` and `/subterra/results/output.h5` are paths inside the container.

### Run calculation with only params file (output will be written to default location)

```bash
docker run --rm \
  -v /absolute/path/to/params.json:/subterra/params.json \
  -v /absolute/path/to/results:/subterra/results \
  subterra-calc /subterra/params.json
```

### Use the Python CLI wrapper

You can also use the provided `main.py` script to simplify running the calculation:

```bash
python main.py simulate --params /absolute/path/to/params.json --output /absolute/path/to/results/output.h5
```

## Additional Docker commands

- **Interactive shell for debugging:**

  ```bash
  docker run --rm -it subterra-calc /bin/bash
  ```

- **Mount additional data:**

  ```bash
  docker run --rm -v /host/data:/subterra/data subterra-calc python src/your_script.py /subterra/data/input.dat
  ```

## Notes

- Always use absolute paths for mounting files and directories.
- The working directory inside the container is `/subterra`.
- The calculation script (`src/simulation/calculation.py`) expects arguments as described above.
- You can extend the image or run other scripts as needed.
