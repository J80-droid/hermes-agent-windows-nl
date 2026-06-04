/** String literals for ARIA boolean attributes (static analyzers + spec). */
export function ariaBool(value: boolean): "true" | "false" {
  return value ? "true" : "false";
}
