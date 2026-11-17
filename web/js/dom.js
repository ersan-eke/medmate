export const el = (tag, props = {}) => Object.assign(document.createElement(tag), props);
export const leafletLink = (s) => el("a", { href: s.url, target: "_blank", rel: "noopener", textContent: `${s.medicine} › ${s.section}` });
