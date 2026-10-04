/**
 * JSON Canonicalization Scheme (RFC 8785), the scheme Suncly uses for `card_hash`
 * and for the signed payload (domain/canonical.py uses the `rfc8785` package).
 *
 * Keys are sorted by UTF-16 code units, which is what JavaScript's default string
 * comparison does; numbers and strings are serialized as JSON.stringify does, which
 * follows the ES6 rules RFC 8785 requires.
 */
export function canonicalize(value: unknown): string {
  if (value === undefined) return "null";
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value) ?? "null";
  }
  if (Array.isArray(value)) {
    return "[" + value.map((item) => canonicalize(item)).join(",") + "]";
  }
  const record = value as Record<string, unknown>;
  const keys = Object.keys(record).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  return (
    "{" +
    keys.map((key) => JSON.stringify(key) + ":" + canonicalize(record[key])).join(",") +
    "}"
  );
}

export function utf8(text: string): Uint8Array {
  return new TextEncoder().encode(text);
}

const SHA256_PREFIX = "sha256:";

/** Lowercase hex SHA-256 with the `sha256:` prefix, as domain/canonical.py writes it. */
export async function sha256Hex(data: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", data as BufferSource);
  return SHA256_PREFIX + hex(new Uint8Array(digest));
}

export function hex(bytes: Uint8Array): string {
  let out = "";
  for (const byte of bytes) out += byte.toString(16).padStart(2, "0");
  return out;
}

export function b64urlDecode(text: string): Uint8Array {
  const padded = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export function subtleAvailable(): boolean {
  return typeof crypto !== "undefined" && typeof crypto.subtle !== "undefined";
}
