# Falafel version2

last update: Nov 30, 2024

A hardware memory allocator; <br>
this allocator supports 
- the first-fit strategy 
- the best-fit strategy
- merge free blocks next to each other

## Related Documents
- the devlopment log →　[dev_log.md](doc/dev_log/dev_log.md)
- the documents → [readme.md](doc/README.md)

## Setting up
Falafel v2 uses [Verilator](https://verilator.org/guide/latest/#) (v5.008) for simulation and [Poetry](https://python-poetry.org/) to manage library version dependencies for running its testbench (we use Cocotb for running the simulation). <br>
these days I prefer Poetry :) <br>

1. install poetry <br>
I reccomend using official installer. <br>
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```
2. setting up the poetry virtual env
    ```bash
    cd falafel-private
    poetry install
    ```
3. install verilator
    ```bash
    source install-verilator.sh
    ```

## Running the test
```bash
cd dev
make
```
