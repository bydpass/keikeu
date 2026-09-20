// Python str.strip()/isspace characters. U+FEFF is deliberately not included.
const coreWhitespace = /[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/u;

function stripCoreOuterWhitespace(value) {
  let start = 0;
  let end = value.length;
  while (start < end && coreWhitespace.test(value[start])) start += 1;
  while (end > start && coreWhitespace.test(value[end - 1])) end -= 1;
  return value.slice(start, end);
}

export function formatTagsCsv(tags) {
  if (!Array.isArray(tags) || tags.some((tag) => typeof tag !== "string")) {
    throw new TypeError("tags must be an array of strings");
  }
  return tags
    .map((tag) => /[",]/u.test(tag) ? `"${tag.replaceAll('"', '""')}"` : tag)
    .join(", ");
}

export function parseTagsCsv(input) {
  if (typeof input !== "string") {
    throw new TypeError("input must be a string");
  }

  const tags = [];
  const fail = (error) => ({ ok: false, input, error });
  let index = 0;

  while (index <= input.length) {
    while (index < input.length && coreWhitespace.test(input[index])) index += 1;

    let value = "";
    if (input[index] === '"') {
      index += 1;
      let closed = false;
      while (index < input.length) {
        if (input[index] !== '"') {
          value += input[index];
          index += 1;
        } else if (input[index + 1] === '"') {
          value += '"';
          index += 2;
        } else {
          closed = true;
          index += 1;
          break;
        }
      }
      if (!closed) return fail("Tags 引号未闭合。");
      while (index < input.length && coreWhitespace.test(input[index])) index += 1;
      if (index < input.length && input[index] !== ",") {
        return fail("Tags 中的双引号位置无效。");
      }
    } else {
      const start = index;
      while (index < input.length && input[index] !== ",") {
        if (input[index] === '"') {
          return fail("Tags 中的双引号位置无效。");
        }
        index += 1;
      }
      value = input.slice(start, index);
    }

    value = stripCoreOuterWhitespace(value);
    if (value && !tags.includes(value)) tags.push(value);
    if (index === input.length) break;
    index += 1;
  }

  return { ok: true, input, tags };
}
