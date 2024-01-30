# Unit tests
Unit tests are handled with `cocotb-test`

## Run tests
Source environment variables + python virtual environment (from root of repo)

Run all tests
```bash
SIM=verilator WAVES=1 pytest -o log_cli=True
```

Clean folder
```bash
cocotb-clean -r
```
