# Munk

The testing engine lives in [`munk-test/`](./munk-test/).

Install, usage, and the source layout are in [munk-test/README.md](./munk-test/README.md). Commands in that file run from inside `munk-test/`.

Build from a checkout of this repository:

```bash
cd munk-test
python3 scripts/update_uv_locks.py
python3 scripts/bootstrap_standalone_dev.py --force
./dist/runtime-dev/bin/munk doctor
```

License: [Apache-2.0](./License.txt).
