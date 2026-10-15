/**
 * High-level JavaScript wrapper for ecCodes WebAssembly
 *
 * Provides a cleaner API over the low-level Emscripten bindings.
 */

class EccodesError extends Error {
    constructor(message, code) {
        super(message);
        this.name = 'EccodesError';
        this.code = code;
    }
}

class CodesHandle {
    constructor(eccodesModule, handle, productKind) {
        this._module = eccodesModule;
        this._handle = handle;
        this._productKind = productKind;
    }

    /**
     * Convert a JS string to a UTF8 string on the WASM heap.
     * Returns a BigInt pointer (required for wasm64 function calls).
     * On wasm64, Emscripten doesn't auto-marshal strings, so we do it manually.
     */
    _strToPtr(str) {
        const ptr = this._module.stringToNewUTF8(str);
        if (!ptr) {
            throw new EccodesError('Failed to allocate string on WASM heap', -1);
        }
        // wasm64 requires BigInt for pointer arguments
        return BigInt(ptr);
    }

    /**
     * Allocate memory on the WASM heap. Returns a BigInt pointer.
     */
    _malloc(size) {
        return BigInt(this._module._malloc(size));
    }

    /**
     * Free memory on the WASM heap. Accepts BigInt or number pointer.
     */
    _free(ptr) {
        this._module._free(ptr);
    }

    /**
     * Read a value from WASM memory at the given pointer.
     * Handles wasm64 BigInt pointers correctly.
     */
    _getValue(ptr, type) {
        const p = Number(ptr);
        const mod = this._module;
        switch (type) {
            case 'i8': return mod.HEAP8[p];
            case 'i16': return mod.HEAP16[p / 2];
            case 'i32': return mod.HEAP32[p / 4];
            case 'i64': return mod.HEAP64[p / 8];
            case 'float': return mod.HEAPF32[p / 4];
            case 'double': return mod.HEAPF64[p / 8];
            default: throw new EccodesError(`Invalid type: ${type}`, -1);
        }
    }

    /**
     * Get a long value for a key
     */
    getLong(key) {
        const valuePtr = this._malloc(8);
        const keyPtr = this._strToPtr(key);
        try {
            const ret = this._module._codes_get_long_wrapper(this._handle, keyPtr, valuePtr);
            if (ret !== 0) {
                throw new EccodesError(this._getError(key), ret);
            }
            return Number(this._getValue(valuePtr, 'i64'));
        } finally {
            this._free(valuePtr);
            this._free(keyPtr);
        }
    }

    /**
     * Get a double value for a key
     */
    getDouble(key) {
        const valuePtr = this._malloc(8);
        const keyPtr = this._strToPtr(key);
        try {
            const ret = this._module._codes_get_double_wrapper(this._handle, keyPtr, valuePtr);
            if (ret !== 0) {
                throw new EccodesError(this._getError(key), ret);
            }
            return this._getValue(valuePtr, 'double');
        } finally {
            this._free(valuePtr);
            this._free(keyPtr);
        }
    }

    /**
     * Get a string value for a key
     */
    getString(key) {
        const keyPtr = this._strToPtr(key);
        const strPtr = this._module._codes_get_string_alloc(this._handle, keyPtr);
        this._free(keyPtr);
        if (!strPtr) {
            throw new EccodesError(this._getError(key), -1);
        }

        try {
            const str = this._module.UTF8ToString(Number(strPtr));
            return str;
        } finally {
            this._module._codes_free_string(strPtr);
        }
    }

    /**
     * Get an array of doubles for a key
     */
    getDoubleArray(key) {
        const sizePtr = this._malloc(8);
        const keyPtr = this._strToPtr(key);
        try {
            const ret = this._module._codes_get_double_array_alloc(this._handle, keyPtr, sizePtr);
            if (!ret) {
                throw new EccodesError(this._getError(key), -1);
            }

            const size = Number(this._getValue(sizePtr, 'i64'));
            const values = [];
            for (let i = 0; i < size; i++) {
                values.push(this._getValue(ret + BigInt(i * 8), 'double'));
            }

            this._module._codes_free_array(ret);
            return values;
        } finally {
            this._free(sizePtr);
            this._free(keyPtr);
        }
    }

    /**
     * Get the size of an array for a key
     */
    getSize(key) {
        const sizePtr = this._malloc(8);
        const keyPtr = this._strToPtr(key);
        try {
            const ret = this._module._codes_get_size_wrapper(this._handle, keyPtr, sizePtr);
            if (ret !== 0) {
                throw new EccodesError(this._getError(key), ret);
            }
            return Number(this._getValue(sizePtr, 'i64'));
        } finally {
            this._free(sizePtr);
            this._free(keyPtr);
        }
    }

    /**
     * Get the native type of a key
     */
    getNativeType(key) {
        const typePtr = this._malloc(4);
        const keyPtr = this._strToPtr(key);
        try {
            const ret = this._module._codes_get_native_type_wrapper(this._handle, keyPtr, typePtr);
            if (ret !== 0) {
                throw new EccodesError(this._getError(key), ret);
            }
            return this._getValue(typePtr, 'i32');
        } finally {
            this._free(typePtr);
            this._free(keyPtr);
        }
    }

    /**
     * Check if a key is missing
     */
    isMissing(key) {
        const keyPtr = this._strToPtr(key);
        try {
            return this._module._codes_is_missing_wrapper(this._handle, keyPtr) !== 0;
        } finally {
            this._free(keyPtr);
        }
    }

    /**
     * Clone this handle
     */
    clone() {
        const clonedHandle = this._module._codes_handle_clone_wrapper(this._handle);
        if (!clonedHandle) {
            throw new EccodesError('Failed to clone handle', -1);
        }
        return new CodesHandle(this._module, clonedHandle, this._productKind);
    }

    /**
     * Delete the handle
     */
    delete() {
        if (this._handle) {
            this._module._codes_handle_delete_wrapper(this._handle);
            this._handle = null;
        }
    }

    /**
     * Get the last error message
     */
    _getError(key) {
        const lastError = this._module.UTF8ToString(Number(
            this._module._codes_get_last_error()));
        return lastError || `Error accessing key '${key}'`;
    }
}

class Eccodes {
    constructor(module) {
        this._module = module;
        this._context = this._module._codes_context_get_default_wrapper();
        /** @type {Map<string, string>} host dir -> virtual mount point */
        this._hostMounts = new Map();
    }

    /**
     * Mount a host directory into the virtual filesystem (lazily, idempotent).
     * Returns the virtual mount point path.
     */
    _mountHostDir(hostDir) {
        const path = require('path');
        const absDir = path.resolve(hostDir);
        if (this._hostMounts.has(absDir)) {
            return this._hostMounts.get(absDir);
        }
        const FS = this._module.FS;
        if (!FS || !FS.filesystems.NODEFS) {
            throw new EccodesError('NODEFS not available in WASM module', -1);
        }
        const mountPoint = `/hostfs/${this._hostMounts.length}`;
        try {
            FS.mkdirTree(mountPoint);
            FS.mount(FS.filesystems.NODEFS, { root: absDir }, mountPoint);
        } catch (e) {
            throw new EccodesError(`Failed to mount host directory ${absDir}: ${e.message}`, -1);
        }
        this._hostMounts.set(absDir, mountPoint);
        return mountPoint;
    }

    /**
     * Resolve a path for use with ecCodes:
     * - If the path exists in the virtual filesystem, use it as-is
     * - Otherwise, if it is a readable host file, lazily mount its
     *   parent directory and return the virtual path
     */
    _resolvePath(filePath) {
        const FS = this._module.FS;
        if (FS && FS.analyzePath(filePath).exists) {
            return filePath;
        }
        const fs = require('fs');
        const path = require('path');
        const hostPath = path.isAbsolute(filePath)
            ? filePath
            : path.resolve(process.cwd(), filePath);
        try {
            if (fs.statSync(hostPath).isFile()) {
                const mountPoint = this._mountHostDir(path.dirname(hostPath));
                return `${mountPoint}/${path.basename(hostPath)}`;
            }
        } catch (e) {
            // Not a host file either; fall through and let ecCodes report the error
        }
        return filePath;
    }

    /**
     * Convert a JS string to a UTF8 string on the WASM heap.
     * Returns a BigInt pointer (required for wasm64 function calls).
     */
    _strToPtr(str) {
        const ptr = this._module.stringToNewUTF8(str);
        if (!ptr) {
            throw new EccodesError('Failed to allocate string on WASM heap', -1);
        }
        return BigInt(ptr);
    }

    /**
     * Allocate memory on the WASM heap. Returns a BigInt pointer.
     */
    _malloc(size) {
        return BigInt(this._module._malloc(size));
    }

    /**
     * Free memory on the WASM heap.
     */
    _free(ptr) {
        this._module._free(ptr);
    }

    /**
     * Read a value from WASM memory at the given pointer.
     * Handles wasm64 BigInt pointers correctly (Emscripten's getValue has issues with BigInt).
     */
    _getValue(ptr, type) {
        const p = Number(ptr);
        const mod = this._module;
        switch (type) {
            case 'i8': return mod.HEAP8[p];
            case 'i16': return mod.HEAP16[p / 2];
            case 'i32': return mod.HEAP32[p / 4];
            case 'i64': return mod.HEAP64[p / 8];
            case 'float': return mod.HEAPF32[p / 4];
            case 'double': return mod.HEAPF64[p / 8];
            default: throw new EccodesError(`Invalid type for _getValue: ${type}`, -1);
        }
    }

    /**
     * Get the ecCodes API version
     */
    getVersion() {
        return this._module._codes_get_version();
    }

    /**
     * Set the definitions path
     */
    setDefinitionsPath(path) {
        const pathPtr = this._strToPtr(path);
        try {
            this._module._codes_context_set_definitions_path_wrapper(this._context, pathPtr);
        } finally {
            this._free(pathPtr);
        }
    }

    /**
     * Set the samples path
     */
    setSamplesPath(path) {
        const pathPtr = this._strToPtr(path);
        try {
            this._module._codes_context_set_samples_path_wrapper(this._context, pathPtr);
        } finally {
            this._free(pathPtr);
        }
    }

    /**
     * Open a GRIB file
     */
    openGrib(path) {
        return this.openFile(path, 0); // PRODUCT_GRIB = 0
    }

    /**
     * Open a BUFR file
     */
    openBufr(path) {
        return this.openFile(path, 1); // PRODUCT_BUFR = 1
    }

    /**
     * Open a file with specified product kind
     */
    openFile(path, productKind = 0) {
        const resolved = this._resolvePath(path);
        // Allocate the path string on the WASM heap (wasm64 requires manual string marshaling)
        const pathPtr = this._strToPtr(resolved);
        try {
            const handle = this._module._wasm_handle_new_from_file(pathPtr, productKind);
            if (!handle) {
                const lastError = this._module.UTF8ToString(Number(
                    this._module._codes_get_last_error()));
                throw new EccodesError(lastError || `Failed to open file: ${path}`, -1);
            }
            return new CodesHandle(this._module, handle, productKind);
        } finally {
            this._free(pathPtr);
        }
    }

    /**
     * Iterate over every message in a multi-message GRIB/BUFR file, calling
     * `cb(handle)` for each. Each handle is deleted automatically after the
     * callback returns — this is the supported way to read files that contain
     * more than one message (openGrib() only returns the first).
     *
     * forEachMessage(filePath, cb)              // GRIB (default)
     * forEachMessage(filePath, productKind, cb)
     */
    forEachMessage(filePath, productKind, cb) {
        if (typeof productKind === 'function') {
            cb = productKind;
            productKind = 0; // PRODUCT_GRIB
        }
        const resolved = this._resolvePath(filePath);
        const pathPtr = this._strToPtr(resolved);
        const itPtr = this._module._wasm_iterator_new(pathPtr);
        this._free(pathPtr);
        if (!itPtr) {
            const lastError = this._module.UTF8ToString(Number(
                this._module._codes_get_last_error()));
            throw new EccodesError(lastError || `Failed to open file: ${filePath}`, -1);
        }
        try {
            while (true) {
                const handlePtr = this._module._wasm_iterator_next(itPtr, productKind);
                if (!handlePtr) break; // end of file
                const handle = new CodesHandle(this._module, handlePtr, productKind);
                try {
                    cb(handle);
                } finally {
                    handle.delete(); // WASM memory has no garbage collector
                }
            }
        } finally {
            this._module._wasm_iterator_free(itPtr);
        }
    }

    /**
     * Count messages in a file
     */
    countInFile(path) {
        const resolved = this._resolvePath(path);
        const pathPtr = this._strToPtr(resolved);
        try {
            const count = this._module._codes_count_in_file_wrapper(pathPtr);
            if (count < 0) {
                const lastError = this._module.UTF8ToString(Number(
                    this._module._codes_get_last_error()));
                throw new EccodesError(lastError || `Failed to count messages in: ${path}`, -1);
            }
            return count;
        } finally {
            this._free(pathPtr);
        }
    }

    /**
     * Mount Node.js filesystem to Emscripten's virtual filesystem
     */
    mountFilesystem(root = '.') {
        const path = require('path');
        const absRoot = path.resolve(root);
        // Already mounted at /data with the same root? No-op.
        if (this._hostMounts.get(absRoot) === '/data') {
            return;
        }
        const FS = this._module.FS;
        if (!FS) {
            throw new EccodesError('Filesystem not available in WASM module', -1);
        }

        // Create mount point if it doesn't exist
        try {
            FS.mkdir('/data', 0o777);
        } catch (e) {
            // Directory already exists
        }

        // Mount Node.js filesystem using NODEFS backend
        FS.mount(this._module.FS.filesystems.NODEFS, { root: absRoot }, '/data');
        this._hostMounts.set(absRoot, '/data');
    }

    /**
     * Write a file to the virtual filesystem
     */
    writeFile(path, data) {
        const FS = this._module.FS;
        if (!FS) {
            throw new EccodesError('Filesystem not available in WASM module', -1);
        }

        // Create parent directories so callers can write to arbitrary paths
        // (e.g. '/work/msg.grib') without pre-creating the directory tree.
        const slash = path.lastIndexOf('/');
        if (slash > 0) {
            const dir = path.substring(0, slash);
            if (dir && !FS.analyzePath(dir).exists) {
                FS.mkdirTree(dir);
            }
        }

        if (typeof data === 'string') {
            FS.writeFile(path, data);
        } else if (Buffer.isBuffer(data)) {
            FS.writeFile(path, new Uint8Array(data));
        } else if (data instanceof Uint8Array) {
            FS.writeFile(path, data);
        } else {
            throw new EccodesError('Unsupported data type', -1);
        }
    }

    /**
     * Read a file from the virtual filesystem
     */
    readFile(path) {
        const FS = this._module.FS;
        if (!FS) {
            throw new EccodesError('Filesystem not available in WASM module', -1);
        }

        return FS.readFile(path);
    }
}

/**
 * Create an Eccodes instance from the WASM module
 */
async function createEccodes(moduleOrPath, options = {}) {
    let module;

    if (moduleOrPath === undefined) {
        // Default to the built WASM module location
        const path = require('path');
        // Try several common locations
        const candidates = [
            path.join(__dirname, '..', 'build', 'eccodes', 'eccodes.js'),  // from wasm/ to repo root build
            path.join(__dirname, 'eccodes.js'),  // same dir as wrapper (when in build/eccodes)
        ];
        let loaded = false;
        const errors = [];
        for (const candidate of candidates) {
            try {
                const mod = require(candidate);
                const createModule = mod.default || mod;
                if (typeof createModule === 'function') {
                    module = await createModule(options);
                    loaded = true;
                    break;
                } else {
                    errors.push(`${candidate}: export is not a function (got ${typeof createModule})`);
                }
            } catch (e) {
                errors.push(`${candidate}: ${e.message}`);
            }
        }
        if (!loaded) {
            throw new EccodesError(
                `Failed to load WASM module. Tried:\n  - ${errors.join('\n  - ')}\n` +
                `Pass the module path explicitly: createEccodes('/path/to/eccodes.js').`, -1
            );
        }
    } else if (typeof moduleOrPath === 'string') {
        // Load from path
        const createModule = require(moduleOrPath);
        module = await createModule(options);
    } else if (typeof moduleOrPath === 'function') {
        // Module creator function
        module = await moduleOrPath(options);
    } else {
        // Already initialized module
        module = moduleOrPath;
    }

    return new Eccodes(module);
}

module.exports = { Eccodes, CodesHandle, EccodesError, createEccodes };