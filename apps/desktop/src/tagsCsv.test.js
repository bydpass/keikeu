import { describe, expect, it } from "vitest";

import { formatTagsCsv, parseTagsCsv } from "./tagsCsv.js";

describe("Tags CSV adapter", () => {
  it("round-trips literal commas and doubled quotes", () => {
    const tags = ["夜车", "重逢,旧友", 'a"b'];
    const input = '夜车, "重逢,旧友", "a""b"';

    expect(formatTagsCsv(tags)).toBe(input);
    expect(parseTagsCsv(input)).toEqual({ ok: true, input, tags });
  });

  it("matches Core outer stripping, drops blanks, and keeps first exact values", () => {
    const input = "\u001c 夜车\u3000, , 夜车, e\u0301, é, \ufeff, \ufeff ";

    expect(parseTagsCsv(input).tags).toEqual(["夜车", "e\u0301", "é", "\ufeff"]);
  });

  it.each([
    ['夜车, "未闭合', "Tags 引号未闭合。"],
    ['夜"车', "Tags 中的双引号位置无效。"],
    ['"夜车"尾部', "Tags 中的双引号位置无效。"],
  ])("blocks malformed quotes without changing the input: %s", (input, error) => {
    expect(parseTagsCsv(input)).toEqual({ ok: false, input, error });
  });

  it("rejects non-string boundaries", () => {
    expect(() => formatTagsCsv(["tag", 1])).toThrow(TypeError);
    expect(() => parseTagsCsv(null)).toThrow(TypeError);
  });
});
