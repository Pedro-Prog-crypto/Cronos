# ecCodes WebAssembly Build

This directory contains the build setup for compiling ecCodes to WebAssembly for use in Node.js.

## Prerequisites

- [Emscripten](https://emscripten.org/) - Install via:
  - **macOS**: `brew install emscripten`
  - **Linux**: Download from https://emscripten.org/docs/getting_started/downloads.html
  - Verify with: `emcc --version`

## Building

```bash
# Basic build (no compression support)
python build_wasm.py

# With JPEG support (OpenJPEG)
python build_wasm.py --enable-jpg

# With AEC compression support
python build_wasm.py  # AEC enabled by default

# With both JPEG and AEC
python build_wasm.py --enable-jpg

# Disable AEC (for smaller builds)
python build_wasm.py --disable-aec

# Release build (optimized)
python build_wasm.py --release --enable-jpg

# Custom output directory
python build_wasm.py --output-dir /path/to/output
```

## Output

The build creates:
- `build/wasm/eccodes/eccodes.js` - JavaScript glue code
- `build/wasm/eccodes/eccodes.wasm` - WebAssembly binary
- `build/wasm/eccodes/resources/` - Definitions and samples (if not using memfs)

### Build Times

- **Basic build**: ~5-10 minutes
- **With JPEG**: ~10-20 minutes (includes OpenJPEG build)
- **With AEC**: ~7-12 minutes (includes libaec build)

## Usage in Node.js

```javascript
const createEccodes = require('./build/wasm/eccodes/eccodes.js');

async function main() {
    const eccodes = await createEccodes();

    // Get version
    const version = eccodes._codes_get_version();
    console.log('ecCodes version:', version);

    // Open a GRIB file
    const handle = eccodes._codes_handle_new_from_file('data.grib', 0);

    // Read values
    const valuePtr = eccodes._malloc(8);
    eccodes._codes_get_double(handle, 'Ni', valuePtr);
    const ni = eccodes.getValue(valuePtr, 'double');
    eccodes._free(valuePtr);

    console.log('Ni:', ni);

    // ⚠️ IMPORTANT: Always delete handles and free pointers to prevent memory leaks
    eccodes._codes_handle_delete_wrapper(handle);
}

main().catch(console.error);
```

### Memory Management (Low-Level API)

**CRITICAL**: When using the low-level Emscripten bindings directly, you must manage all memory manually:

```javascript
// ✓ Correct - manual memory management
const handle = eccodes._codes_handle_new_from_file('data.grib', 0);
const ptr = eccodes._malloc(8);
eccodes._codes_get_long(handle, 'Ni', ptr);
eccodes._free(ptr);
eccodes._codes_handle_delete_wrapper(handle);

// ✗ Incorrect - memory leak
const handle = eccodes._codes_handle_new_from_file('data.grib', 0);
const ptr = eccodes._malloc(8);
eccodes._codes_get_long(handle, 'Ni', ptr);
// Memory never freed!
```

**Resources requiring cleanup:**
- Handles: `_codes_handle_delete_wrapper(handle)`
- Allocated pointers: `_free(ptr)`

## Current Limitations

### v1.0
- **Node.js only** - Browser support planned for v2.0
- **Manual memory management** - Must explicitly free handles and pointers
- **No TypeScript definitions** - Coming in v2.0
- **PNG disabled** - libpng requires additional configuration
- **File I/O** - Uses Emscripten's virtual filesystem; files must be preloaded
- **Memory** - Limited to 512MB by default (configurable in build_wasm.py)

1. **PNG disabled** - libpng requires additional configuration
2. **File I/O** - Uses Emscripten's virtual filesystem; files must be preloaded
3. **Memory** - Limited to 512MB by default (configurable in build_wasm.py)
4. **Build time** - Building OpenJPEG adds ~2-5 minutes to build time

### Compression Support

- **JPEG (OpenJPEG)** - Use `--enable-jpg` flag. Builds OpenJPEG v2.5.2 with Emscripten
- **AEC (libaec)** - Enabled by default, disable with `--disable-aec` flag
- **PNG (libpng)** - Not yet supported (requires libpng build configuration)

## Loading Files in WASM

To load files from the filesystem into the Emscripten virtual filesystem:

```javascript
const fs = require('fs');
const eccodes = await createEccodes();

// Mount Node.js filesystem
eccodes.FS.mkdir('/data');
eccodes.FS.mount(fs, { root: '.' }, '/data');

// Now files are accessible via /data/filename.grib
const handle = eccodes._codes_handle_new_from_file('/data/sample.grib', 0);
```

## Development

To extend the bindings:

1. Add functions to `eccodes_wrapper.c` with `EMSCRIPTEN_KEEPALIVE` macro
2. Rebuild with `python build_wasm.py`
3. Call via `eccodes._function_name()` from JavaScript

## Alternative: Rust + wasm-bindgen

If you prefer Rust bindings, an alternative approach is:

```bash
cd rust/crates
cargo new --lib eccodes-wasm
cd eccodes-wasm
# Add wasm-bindgen and eccodes-sys dependencies
wasm-pack build --target nodejs
```

This leverages the existing Rust FFI bindings but requires configuring the C library
build for the `wasm32-unknown-unknown` target.