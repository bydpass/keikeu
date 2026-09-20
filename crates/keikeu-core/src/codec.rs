use super::{Error, Result};
use chrono::{Datelike, NaiveDate};
use serde::{Deserialize, Serialize};
use serde_json::Value;

const START: &str = "<!-- keikeu:page ";
const SUFFIX: &str = " -->";
const END: &str = "<!-- /keikeu:page -->";
const RESERVED: &[&str] = &[
    "type",
    "schema_version",
    "code",
    "created",
    "updated",
    "display_name",
    "legacy_title",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Page {
    pub name: Option<String>,
    pub content: String,
    pub r#type: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Paper {
    pub code: String,
    pub created: String,
    pub updated: String,
    pub display_name: Option<String>,
    pub legacy_title: Option<String>,
    pub pages: Vec<Page>,
    pub tags: Vec<String>,
    pub extra_frontmatter: Vec<(String, String)>,
}

fn whitespace(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}
fn trim(s: &str) -> &str {
    s.trim_matches(whitespace)
}
fn invalid_name_char(c: char) -> bool {
    c.is_control() || c == '\u{2028}' || c == '\u{2029}'
}

fn name(value: &Option<String>) -> Result<Option<String>> {
    let Some(value) = value else { return Ok(None) };
    let value = trim(value);
    if value.is_empty() {
        return Ok(None);
    }
    if value.chars().count() > 200 || value.chars().any(invalid_name_char) {
        return Err(Error::format("invalid_name"));
    }
    Ok(Some(value.to_owned()))
}

// Unicode decimal block starts from Python's supported Unicode database. Codes
// preserve digits verbatim: the existing Python contract also accepts Nd suffixes.
fn decimal(c: char) -> Option<u32> {
    super::unicode_data::DECIMAL_ZEROES
        .iter()
        .find_map(|zero| (c as u32).checked_sub(*zero).filter(|n| *n < 10))
}

pub fn code_sequence(code: &str) -> Option<u32> {
    validate_code(code).ok()?;
    code.chars()
        .skip(11)
        .try_fold(0, |n, c| decimal(c).map(|digit| n * 10 + digit))
}

pub fn validate_code(code: &str) -> Result<()> {
    let chars: Vec<_> = code.chars().collect();
    if chars.len() != 14 || !code.starts_with("K-") || chars[10] != '-' {
        return Err(Error::format("invalid_code"));
    }
    let date: String = chars[2..10].iter().collect();
    if !date.bytes().all(|b| b.is_ascii_digit())
        || !NaiveDate::parse_from_str(&date, "%Y%m%d").is_ok_and(|d| d.year() >= 1)
    {
        return Err(Error::format("invalid_code_date"));
    }
    let digits: Option<Vec<_>> = chars[11..].iter().map(|c| decimal(*c)).collect();
    if digits.is_none_or(|digits| digits.iter().all(|n| *n == 0)) {
        return Err(Error::format("invalid_code_sequence"));
    }
    Ok(())
}

fn number(s: &str) -> Result<u32> {
    if s.is_empty() || !s.bytes().all(|b| b.is_ascii_digit()) {
        return Err(Error::format("invalid_datetime"));
    }
    s.parse().map_err(|_| Error::format("invalid_datetime"))
}

fn time_parts(s: &str) -> Result<(u32, u32, u32, u32)> {
    let (whole, fraction) = s.split_once(['.', ',']).unwrap_or((s, ""));
    if s.contains(['.', ','])
        && (fraction.is_empty() || !fraction.bytes().all(|b| b.is_ascii_digit()))
    {
        return Err(Error::format("invalid_datetime"));
    }
    let parts: Vec<_> = if whole.contains(':') {
        whole.split(':').collect()
    } else if whole.is_ascii() && matches!(whole.len(), 2 | 4 | 6) {
        (0..whole.len())
            .step_by(2)
            .map(|i| &whole[i..i + 2])
            .collect()
    } else {
        return Err(Error::format("invalid_datetime"));
    };
    if parts.is_empty() || parts.len() > 3 || parts.iter().any(|p| p.len() != 2) {
        return Err(Error::format("invalid_datetime"));
    }
    let h = number(parts[0])?;
    let m = if parts.len() > 1 {
        number(parts[1])?
    } else {
        0
    };
    let sec = if parts.len() > 2 {
        number(parts[2])?
    } else {
        0
    };
    let mut micro = fraction.chars().take(6).collect::<String>();
    while micro.len() < 6 {
        micro.push('0')
    }
    Ok((h, m, sec, number(&micro)?))
}

fn datetime(s: &str) -> Result<String> {
    // Python fromisoformat accepts calendar/basic/week dates and a single separator.
    let mut found = None;
    for (len, format) in [
        (10, "%Y-%m-%d"),
        (8, "%Y%m%d"),
        (10, "%G-W%V-%u"),
        (8, "%GW%V%u"),
    ] {
        if let Some(prefix) = s.get(..len) {
            if let Ok(date) = NaiveDate::parse_from_str(prefix, format) {
                found = Some((date, len));
                break;
            }
        }
    }
    if found.is_none() {
        for (len, suffix, format) in [(8, "-1", "%G-W%V-%u"), (7, "1", "%GW%V%u")] {
            if let Some(prefix) = s.get(..len) {
                if let Ok(date) = NaiveDate::parse_from_str(&format!("{prefix}{suffix}"), format) {
                    found = Some((date, len));
                    break;
                }
            }
        }
    }
    let (date, len) = found.ok_or_else(|| Error::format("invalid_datetime"))?;
    if date.year() < 1 || date.year() > 9999 {
        return Err(Error::format("invalid_datetime"));
    }
    let rest = &s[len..];
    if rest.is_empty() {
        return Ok(format!("{}T00:00:00", date.format("%Y-%m-%d")));
    }
    let separator = rest.chars().next().unwrap().len_utf8();
    let time = &rest[separator..];
    let zone_at = time.find(['+', '-', 'Z']).unwrap_or(time.len());
    let (h, m, sec, micro) = time_parts(&time[..zone_at])?;
    if h > 23 || m > 59 || sec > 59 {
        return Err(Error::format("invalid_datetime"));
    }
    let mut out = format!("{}T{h:02}:{m:02}:{sec:02}", date.format("%Y-%m-%d"));
    if micro != 0 {
        out.push_str(&format!(".{micro:06}"));
    }
    let zone = &time[zone_at..];
    if zone == "Z" {
        out.push_str("+00:00")
    } else if !zone.is_empty() {
        let (zh, zm, zs, zu) = time_parts(&zone[1..])?;
        let seconds = u64::from(zh) * 3600 + u64::from(zm) * 60 + u64::from(zs);
        if seconds >= 86400 {
            return Err(Error::format("invalid_datetime"));
        }
        let sign = if seconds == 0 && zu == 0 {
            '+'
        } else {
            zone.chars().next().unwrap()
        };
        out.push_str(&format!(
            "{sign}{:02}:{:02}",
            seconds / 3600,
            seconds / 60 % 60
        ));
        if seconds % 60 != 0 || zu != 0 {
            out.push_str(&format!(":{:02}", seconds % 60))
        }
        if zu != 0 {
            out.push_str(&format!(".{zu:06}"))
        }
    }
    Ok(out)
}

impl Paper {
    pub fn normalized(&self) -> Result<Self> {
        validate_code(&self.code)?;
        let mut p = self.clone();
        p.created = datetime(&p.created)?;
        p.updated = datetime(&p.updated)?;
        p.display_name = name(&p.display_name)?;
        if p.pages.is_empty() {
            return Err(Error::format("missing_pages"));
        }
        let mut summaries = 0;
        for (index, page) in p.pages.iter_mut().enumerate() {
            let validate = || -> Result<Option<String>> {
                let n = name(&page.name)?;
                if n.is_none() && trim(&page.content).is_empty() {
                    return Err(Error::format("empty_page"));
                }
                if !matches!(
                    page.r#type.as_deref(),
                    None | Some("summary" | "snapshot" | "whisper")
                ) {
                    return Err(Error::format("invalid_page_type"));
                }
                Ok(n)
            };
            page.name = validate().map_err(|mut e| {
                e.page_number = Some(index + 1);
                e
            })?;
            if page.r#type.as_deref() == Some("summary") {
                summaries += 1;
                if summaries > 1 {
                    let mut e = Error::format("multiple_summary_pages");
                    e.page_number = Some(index + 1);
                    return Err(e);
                }
            }
        }
        if summaries > 1 {
            return Err(Error::format("multiple_summary_pages"));
        }
        p.tags.clear();
        for value in &self.tags {
            let tag = trim(value);
            if tag.is_empty() {
                continue;
            }
            if tag.chars().any(invalid_name_char) {
                return Err(Error::format("invalid_tag"));
            }
            if !p.tags.iter().any(|v| v == tag) {
                p.tags.push(tag.to_owned())
            }
        }
        let mut keys = Vec::new();
        for (k, _) in &p.extra_frontmatter {
            if trim(k) != k
                || k.is_empty()
                || k.contains(':')
                || k.chars().any(invalid_name_char)
                || RESERVED.contains(&k.as_str())
                || keys.contains(k)
            {
                return Err(Error::format("invalid_frontmatter_key"));
            }
            keys.push(k.clone());
        }
        Ok(p)
    }
}

fn scalar(s: &str) -> String {
    s.replace('\\', "\\\\")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
}
fn unscalar(s: &str) -> String {
    let mut out = String::new();
    let mut chars = s.chars();
    while let Some(c) = chars.next() {
        if c == '\\' {
            match chars.next() {
                Some('n') => out.push('\n'),
                Some('r') => out.push('\r'),
                Some('\\') => out.push('\\'),
                Some(other) => {
                    out.push('\\');
                    out.push(other)
                }
                None => out.push('\\'),
            }
        } else {
            out.push(c)
        }
    }
    out
}
fn marker(s: &str) -> bool {
    s.starts_with(START) && s.ends_with(SUFFIX)
}
fn reserved(s: &str) -> bool {
    let s = s.trim_start_matches('\\');
    s == END || marker(s)
}

pub fn render(p: &Paper) -> Result<Vec<u8>> {
    let p = p.normalized()?;
    let mut fields = vec![
        ("type".into(), "paper".into()),
        ("schema_version".into(), "4".into()),
        ("code".into(), p.code.clone()),
        ("created".into(), p.created),
        ("updated".into(), p.updated),
    ];
    if let Some(n) = p.display_name {
        fields.push(("display_name".into(), n));
    }
    if let Some(n) = p.legacy_title {
        fields.push(("legacy_title".into(), n));
    }
    fields.extend(p.extra_frontmatter);
    let mut out = "---\n".to_string();
    for (k, v) in fields {
        out.push_str(&format!("{k}: {}\n", scalar(&v)));
    }
    out.push_str(&format!("---\n# {}\n\n", p.code));
    for page in p.pages {
        let n = serde_json::to_string(&page.name)
            .unwrap()
            .replace('-', "\\u002d");
        let t = serde_json::to_string(&page.r#type).unwrap();
        out.push_str(&format!("{START}{{\"name\":{n},\"type\":{t}}}{SUFFIX}\n"));
        if !page.content.is_empty() {
            for line in page.content.split('\n') {
                if reserved(line) {
                    out.push('\\');
                }
                out.push_str(line);
                out.push('\n');
            }
        }
        out.push_str(END);
        out.push_str("\n\n");
    }
    out.push_str("## Tags");
    if !p.tags.is_empty() {
        out.push('\n');
        for tag in p.tags {
            out.push_str(&format!("\n- {tag}"));
        }
    }
    out.push('\n');
    Ok(out.into_bytes())
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Marker {
    name: Value,
    r#type: Value,
}
fn nullable(value: Value) -> Result<Option<String>> {
    match value {
        Value::Null => Ok(None),
        Value::String(s) => Ok(Some(s)),
        _ => Err(Error::format("invalid_page_metadata")),
    }
}

pub fn parse(bytes: &[u8]) -> Result<Paper> {
    let raw = std::str::from_utf8(bytes).map_err(|_| Error::format("invalid_utf8"))?;
    if raw.starts_with('\u{feff}') {
        return Err(Error::format("utf8_bom"));
    }
    if raw.contains('\r') && raw.replace("\r\n", "").contains(['\r', '\n']) {
        return Err(Error::format("invalid_line_endings"));
    }
    let normalized = raw.replace("\r\n", "\n");
    let text = normalized.strip_suffix('\n').unwrap_or(&normalized);
    let lines: Vec<_> = text.split('\n').collect();
    if lines.first() != Some(&"---") {
        return Err(Error::format("missing_frontmatter"));
    }
    let mut fields: Vec<(String, String)> = Vec::new();
    let mut i = 1;
    while i < lines.len() && lines[i] != "---" {
        let (k, v) = lines[i]
            .split_once(':')
            .ok_or_else(|| Error::format("invalid_frontmatter"))?;
        let key = trim(k);
        if key.is_empty()
            || key.chars().any(invalid_name_char)
            || fields.iter().any(|(k, _)| k == key)
        {
            return Err(Error::format("invalid_frontmatter_key"));
        }
        fields.push((key.into(), unscalar(trim(v))));
        i += 1;
    }
    if i >= lines.len() {
        return Err(Error::format("missing_frontmatter_end"));
    }
    let get = |k: &str| {
        fields
            .iter()
            .find(|(key, _)| key == k)
            .map(|(_, v)| v.clone())
    };
    let required = |k| get(k).ok_or_else(|| Error::format("missing_frontmatter_field"));
    if required("type")? != "paper" || required("schema_version")? != "4" {
        return Err(Error::format("wrong_schema"));
    }
    let mut p = Paper {
        code: required("code")?,
        created: required("created")?,
        updated: required("updated")?,
        display_name: get("display_name"),
        legacy_title: get("legacy_title"),
        pages: vec![],
        tags: vec![],
        extra_frontmatter: fields
            .iter()
            .filter(|(k, _)| !RESERVED.contains(&k.as_str()))
            .cloned()
            .collect(),
    };
    i += 1;
    if lines.get(i).copied() != Some(format!("# {}", p.code).as_str())
        || lines.get(i + 1) != Some(&"")
    {
        return Err(Error::format("invalid_heading"));
    }
    i += 2;
    while i < lines.len() && marker(lines[i]) {
        let payload = &lines[i][START.len()..lines[i].len() - SUFFIX.len()];
        let mut page_parse = || -> Result<Page> {
            if payload.contains("--") {
                return Err(Error::format("raw_comment_hyphens"));
            }
            let meta: Marker =
                serde_json::from_str(payload).map_err(|_| Error::format("invalid_page_json"))?;
            i += 1;
            let mut content = Vec::new();
            while i < lines.len() && lines[i] != END {
                if marker(lines[i]) {
                    return Err(Error::format("nested_page"));
                }
                let line = lines[i];
                content.push(if line.starts_with('\\') && reserved(line) {
                    &line[1..]
                } else {
                    line
                });
                i += 1;
            }
            if i >= lines.len() {
                return Err(Error::format("missing_page_end"));
            }
            i += 1;
            if lines.get(i) != Some(&"") {
                return Err(Error::format("missing_page_separator"));
            }
            i += 1;
            Ok(Page {
                name: nullable(meta.name)?,
                r#type: nullable(meta.r#type)?,
                content: content.join("\n"),
            })
        };
        p.pages.push(page_parse().map_err(|mut e| {
            e.page_number = Some(p.pages.len() + 1);
            e
        })?);
    }
    if lines.get(i) != Some(&"## Tags") {
        return Err(Error::format("missing_tags"));
    }
    i += 1;
    if i < lines.len() {
        if lines[i] != "" || i + 1 >= lines.len() {
            return Err(Error::format("invalid_tags_separator"));
        }
        i += 1;
        while i < lines.len() {
            let tag = lines[i]
                .strip_prefix("- ")
                .ok_or_else(|| Error::format("invalid_tag_item"))?;
            if trim(tag).is_empty() {
                return Err(Error::format("empty_tag"));
            }
            p.tags.push(tag.into());
            i += 1;
        }
    }
    p.normalized()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn shared_python_golden() {
        let corpus: Value =
            serde_json::from_str(include_str!("../../../tests/fixtures/paper-v4-golden.json"))
                .unwrap();
        for case in corpus["cases"].as_array().unwrap() {
            let hex = case["hex"].as_str().unwrap();
            let bytes: Vec<u8> = (0..hex.len())
                .step_by(2)
                .map(|i| u8::from_str_radix(&hex[i..i + 2], 16).unwrap())
                .collect();
            let result = parse(&bytes);
            if case.get("error").is_some() {
                assert!(result.is_err(), "{}", case["name"]);
            } else {
                let p = result.unwrap_or_else(|e| panic!("{}: {:?}", case["name"], e));
                assert_eq!(
                    serde_json::to_value(&p).unwrap(),
                    case["paper"],
                    "{}",
                    case["name"]
                );
                assert_eq!(
                    String::from_utf8(render(&p).unwrap()).unwrap(),
                    case["canonical"].as_str().unwrap(),
                    "{}",
                    case["name"]
                );
            }
        }
    }
}
