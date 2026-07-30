import assert from "node:assert/strict";
import test from "node:test";

import {
  bytesFromFileSize,
  fileSizeInputFromBytes,
  isFileSizeBoundaryValid,
  isFileSizeRangeValid,
} from "../src/utils/fileSizeFilter.js";

test("converts file size inputs to exact byte values", () => {
  assert.equal(bytesFromFileSize(1, "MB"), 1024 ** 2);
  assert.equal(bytesFromFileSize("1.5", "GB"), 1.5 * 1024 ** 3);
  assert.equal(bytesFromFileSize("", "MB"), null);
  assert.ok(Number.isNaN(bytesFromFileSize(-1, "MB")));
});

test("round-trips stored byte boundaries without precision loss", () => {
  assert.deepEqual(fileSizeInputFromBytes(1024 ** 3), { value: 1, unit: "GB" });
  assert.deepEqual(fileSizeInputFromBytes(1536), { value: 1.5, unit: "KB" });
  assert.deepEqual(fileSizeInputFromBytes(null), { value: null, unit: "MB" });
});

test("validates nullable boundaries and inclusive ranges", () => {
  assert.equal(isFileSizeBoundaryValid(null), true);
  assert.equal(isFileSizeBoundaryValid(0), true);
  assert.equal(isFileSizeBoundaryValid(1.5), false);
  assert.equal(isFileSizeRangeValid(1024, 1024), true);
  assert.equal(isFileSizeRangeValid(2048, 1024), false);
});
