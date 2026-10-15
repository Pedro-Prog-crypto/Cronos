/**
 * @meri-imperiumi/eccodes-wasm
 *
 * WebAssembly build of ECMWF ecCodes for Node.js
 *
 * Usage:
 *   const { createEccodes } = require('@meri-imperiumi/eccodes-wasm');
 *   const eccodes = await createEccodes();
 *   const handle = eccodes.openFile('/path/to/file.grib');
 */

module.exports = require('./wasm/eccodes.js');
