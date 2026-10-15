# eccodes-wasm

WebAssembly (WASM) build of [ECMWF ecCodes](https://github.com/ecmwf/eccodes) for Node.js and browsers.

**Package**: `@meri-imperiumi/eccodes-wasm`

Decode GRIB and BUFR meteorological data files in JavaScript using the same library trusted by weather services worldwide.

## Features

- ✅ **Full GRIB support** - GRIB edition 1 and 2
- ✅ **Full BUFR support** - BUFR edition 3 and 4
- ✅ **Compression** - AEC and JPEG (optional)
- ✅ **Node.js 18+** - Modern JavaScript support
- ✅ **Type-safe API** - High-level wrapper with error handling
- ✅ **Small footprint** - Only ~5-10 MB WASM binary

## Quick Start

### Prerequisites

```bash
# macOS
brew install emscripten cmake

# Linux (Ubuntu/Debian)
apt-get install emscripten cmake git

# Verify
emcc --version  # Should show Emscripten 3.1+
cmake --version # Should show CMake 3.20+
```

### Setup

**Option A: Git Submodule (recommended for development)**

```bash
make setup TAG=2.49.0
```

**Option B: Release Tarball (recommended for production)**

```bash
make download VERSION=2.49.0
```

### Build

```bash
# With JPEG support (recommended)
make build-jpg

# Or for production (optimized)
make release
```

### Usage

```javascript
const { createEccodes } = require('./build/eccodes/index.js');

async function main() {
    const eccodes = await createEccodes();

    // Mount filesystem
    eccodes.mountFilesystem('.');

    // Open a GRIB file
    const handle = eccodes.openGrib('sample.grib');

    // Read metadata
    console.log('Name:', handle.getString('name'));
    console.log('Units:', handle.getString('units'));
    console.log('Grid size:', `${handle.getLong('Ni')}x${handle.getLong('Nj')}`);

    // Read data values
    const values = handle.getDoubleArray('values');
    console.log(`Read ${values.length} values`);

    // ⚠️ IMPORTANT: Always delete handles to free WASM memory
    handle.delete();
}

main();
```

### Memory Management

**CRITICAL**: WebAssembly does not have automatic garbage collection for C-allocated memory. You must manually free resources:

```javascript
// ✓ Correct - manual cleanup
const handle = eccodes.openGrib('file.grib');
// ... use handle ...
handle.delete();  // Frees WASM memory

// ✗ Incorrect - memory leak
const handle = eccodes.openGrib('file.grib');
// ... use handle ...
// Memory never freed!
```

## Documentation

- [WASM Build Guide](./wasm/README.md) - Detailed WASM build documentation
- [Quick Start](./wasm/QUICKSTART.md) - Quick reference guide
- [Publishing Guide](./docs/wasm/PUBLISHING.md) - NPM publishing with OIDC
- [Repository Structure](./docs/wasm/REPOSITORY_STRUCTURE.md) - Complete structure docs
- [Fresh Repository Setup](./docs/wasm/FRESH_REPO_SETUP.md) - Creating a new repo
- [Migration Guide](./docs/wasm/MIGRATION_GUIDE.md) - Migrating from eccodes/

## Build Options

| Target | Description | Time |
|--------|-------------|------|
| `make build` | Debug, AEC only | ~5-10 min |
| `make build-jpg` | Debug, AEC + JPEG | ~10-20 min |
| `make release` | Release, AEC + JPEG | ~10-20 min |

### Compression Support

| Codec | Default | Size | Build Time |
|-------|---------|------|------------|
| AEC | ✅ Yes | +500 KB | +2-3 min |
| JPEG | ❌ No | +2 MB | +8-10 min |

Enable JPEG: `python wasm/build_wasm.py --enable-jpg`

## API Reference

### Memory Lifecycle

| Resource | Created By | Must Be Freed By |
|----------|------------|-----------------|
| `CodesHandle` | `openGrib()`, `openBufr()` | `handle.delete()` |
| String buffers | `getString()` (internal) | Automatic |
| Array buffers | `getDoubleArray()` (internal) | Automatic |

Only `CodesHandle` objects require manual cleanup.

```javascript
// Create instance
const eccodes = await createEccodes();

// Version
eccodes.getVersion();

// Configuration
eccodes.setDefinitionsPath('/path/to/definitions');
eccodes.setSamplesPath('/path/to/samples');

// Open files
const grib = eccodes.openGrib('file.grib');
const bufr = eccodes.openBufr('file.bufr');
const count = eccodes.countInFile('file.grib');

// Read values
grib.getLong('Ni');              // number
grib.getDouble('latitude');      // number
grib.getString('name');          // string
grib.getDoubleArray('values');   // number[]

// Metadata
grib.getSize('values');          // array length
grib.getNativeType('Ni');        // type constant
grib.isMissing('missingKey');    // boolean

// Cleanup
grib.delete();
```

## Development

### Update ecCodes Version

Update the version pinned in `ECCODES_VERSION` (what CI builds
against), then update your local checkout:

```bash
# Git submodule
make setup TAG=2.50.0

# Release tarball
make download VERSION=2.50.0 --clean
```

### Run Tests

```bash
make test
```

### Run Example

```bash
make example
```

### Clean Build

```bash
make clean
make release
```

## Repository Structure

```
eccodes-wasm/
├── eccodes/          # ecCodes source (git submodule or extracted)
├── wasm/             # WASM build configuration
├── scripts/          # Setup and download scripts
├── .github/          # CI/CD workflows
├── docs/wasm/        # Documentation
├── Makefile          # Build targets
└── README.md         # This file
```

See [Repository Structure](./docs/wasm/REPOSITORY_STRUCTURE.md) for details.

## Publishing

### Automated (Recommended)

```bash
git tag v2.48.2
git push origin v2.48.2
```

Triggers GitHub Actions to build, test, and publish via OIDC.
The tag sets the NPM version; CI builds against the ecCodes
version pinned in the [ECCODES_VERSION](./ECCODES_VERSION) file.

### Manual

```bash
make release
npm token create --ci
npm config set //registry.npmjs.org/:_authToken <token>
npm publish --access public
```

See [Publishing Guide](./docs/wasm/PUBLISHING.md) for details.

## License

Apache License 2.0

### Third-Party Licenses

- **ecCodes**: [Apache 2.0](https://github.com/ecmwf/eccodes/blob/master/LICENSE) - ECMWF
- **OpenJPEG**: [BSD 2-Clause](https://github.com/uclouvain/openjpeg/blob/master/LICENSE) - uCLouvain
- **libaec**: [BSD 2-Clause](https://gitlab.dkrz.de/k202009/libaec/-/blob/master/COPYING) - DKRZ

## Contributing

Contributions welcome! See [docs/wasm/MIGRATION_GUIDE.md](./docs/wasm/MIGRATION_GUIDE.md) for development workflow.

## Related Projects

- [ecCodes](https://github.com/ecmwf/eccodes) - C library
- [eccodes-js](https://github.com/naturalintelligence/eccodes-js) - Node.js via FFI
- [pyeccodes](https://pypi.org/project/eccodes/) - Python bindings

## Support

- **Issues**: [GitHub Issues](https://github.com/meri-imperiumi/eccodes-wasm/issues)
- **ecCodes Docs**: [ecmwf.int](https://confluence.ecmwf.int/display/ECC/ecCodes+Home)