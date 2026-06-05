import { describe, expect, it } from "vitest";

import { assertJsonObject, assertJsonValue } from "../src/types/contracts";

describe("JSON contract guards", () => {
  it("accepts nested JSON values", () => {
    const value: unknown = {
      scope: "critical_reviews",
      confidence: 0.72,
      flags: [true, false, null],
      nested: {
        asin: "B000000001",
        pages: [1, 2, 3]
      }
    };

    expect(() => assertJsonValue(value)).not.toThrow();
    expect(() => assertJsonObject(value)).not.toThrow();
  });

  it("rejects non-finite numbers before JSON.stringify can coerce them to null", () => {
    expect(() => assertJsonValue(Number.NaN)).toThrow("json_number_must_be_finite");
    expect(() => assertJsonValue(Number.POSITIVE_INFINITY)).toThrow("json_number_must_be_finite");
    expect(() => assertJsonValue(Number.NEGATIVE_INFINITY)).toThrow("json_number_must_be_finite");
  });

  it("rejects non-JSON runtime values", () => {
    const rejectedValues: unknown[] = [
      new Date("2026-06-05T00:00:00.000Z"),
      new Map([["key", "value"]]),
      new Set(["value"]),
      undefined,
      () => "value"
    ];

    for (const value of rejectedValues) {
      expect(() => assertJsonValue(value)).toThrow();
    }
  });

  it("rejects non-JSON values nested in objects and arrays", () => {
    expect(() => assertJsonValue({ value: undefined })).toThrow();
    expect(() => assertJsonValue([() => "value"])).toThrow();
  });

  it("rejects object keys that JSON.stringify would ignore", () => {
    const symbolKey = Symbol("hidden");
    expect(() => assertJsonValue({ [symbolKey]: "value" })).toThrow(
      "json_object_keys_must_be_strings"
    );
  });

  it("requires assertJsonObject values to be plain objects", () => {
    expect(() => assertJsonObject(["value"])).toThrow("json_object_required");
    expect(() => assertJsonObject(null)).toThrow("json_object_required");
  });
});
