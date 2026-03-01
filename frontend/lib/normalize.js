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

    const label =
      (typeof item.key === "string" && item.key) ||
      (typeof item.label === "string" && item.label) ||
      (typeof item.name === "string" && item.name) ||
      (typeof item.title === "string" && item.title) ||
      "";

    const hasValue =
      Object.prototype.hasOwnProperty.call(item, "value") &&
      item.value !== undefined &&
      item.value !== null;
    const unit =
      Object.prototype.hasOwnProperty.call(item, "unit") &&
      item.unit !== undefined &&
      item.unit !== null
        ? String(item.unit)
        : "";

    if (label && hasValue) {
      return `${label}: ${String(item.value)}${unit ? ` ${unit}` : ""}`;
    }
    if (label) {
      return label;
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
