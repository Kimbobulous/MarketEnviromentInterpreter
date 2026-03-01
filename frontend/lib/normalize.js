export function asText(item) {
  if (typeof item === "string") {
    return item;
  }

  if (typeof item === "number" || typeof item === "boolean") {
    return String(item);
  }

  if (item && typeof item === "object") {
    if (typeof item.text === "string") {
      return item.text;
    }
    if (typeof item.title === "string") {
      return item.title;
    }
    try {
      return JSON.stringify(item);
    } catch {
      return "[object]";
    }
  }

  return "";
}

export function normalizeList(items) {
  const isNonEmpty = (value) => typeof value === "string" && value.trim() !== "";

  if (Array.isArray(items)) {
    return items.map(asText).filter(isNonEmpty);
  }

  if (typeof items === "string" || (items && typeof items === "object")) {
    const text = asText(items);
    return isNonEmpty(text) ? [text] : [];
  }

  return [];
}
