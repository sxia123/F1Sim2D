// Precision Vector Constructor Emblems (Inline SVG + Pre-Rasterized Canvas Image Cache)

const LOGO_SVGS = {
  mercedes: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="14" fill="#0b1017" stroke="#c8d2de" stroke-width="1.8"/>
    <circle cx="16" cy="16" r="11.6" fill="none" stroke="#00d2be" stroke-width="1.2" opacity="0.95"/>
    <circle cx="16" cy="16" r="9.4" fill="none" stroke="#334155" stroke-width="0.6"/>
    <path d="M16 3.5 L18.2 14.3 L27.2 22.4 L16 17.8 L4.8 22.4 L13.8 14.3 Z" fill="#f1f5f9" stroke="#94a3b8" stroke-width="0.5"/>
    <path d="M16 3.5 L16 17.8 L4.8 22.4 L13.8 14.3 Z" fill="#cbd5e1" opacity="0.55"/>
    <circle cx="16" cy="16" r="1.6" fill="#00d2be" stroke="#ffffff" stroke-width="0.5"/>
  </svg>`,

  ferrari: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <path d="M6 3.5 H26 V17 C26 23.8 20.8 28 16 29.8 C11.2 28 6 23.8 6 17 Z" fill="#ffdf00" stroke="#111111" stroke-width="1.5"/>
    <path d="M7.2 11.2 H24.8 V16.8 C24.8 22.6 20.4 26.2 16 27.9 C11.6 26.2 7.2 22.6 7.2 16.8 Z" fill="none" stroke="#d97706" stroke-width="0.6" opacity="0.55"/>
    <rect x="6.7" y="4.3" width="18.6" height="2.2" fill="#009246"/>
    <rect x="6.7" y="6.5" width="18.6" height="2.1" fill="#ffffff"/>
    <rect x="6.7" y="8.6" width="18.6" height="2.2" fill="#ce2b37"/>
    <path d="M16.5 12.2 C18.8 12.2 19.6 14 18.4 15.8 L20.2 18.6 L18.2 19.2 L16.8 17.2 L15.4 20.8 L17.6 22.6 H13.2 L14.1 18.4 L12.3 16.5 L14.2 14.2 C14.6 12.8 15.4 12.2 16.5 12.2 Z" fill="#111111"/>
    <text x="16" y="26.4" text-anchor="middle" font-family="Arial,sans-serif" font-weight="900" font-size="5.2" fill="#ce2b37">SF</text>
  </svg>`,

  redbull: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="5.5" width="28" height="21" rx="3.5" fill="#101c42" stroke="#3671c6" stroke-width="1.6"/>
    <path d="M3 8 H29" stroke="#e10600" stroke-width="1.1" opacity="0.85"/>
    <circle cx="16" cy="16.2" r="5.8" fill="#ffd200" stroke="#f59e0b" stroke-width="0.8"/>
    <path d="M4.2 19.5 L8.5 14.2 L13.8 15.2 L15.2 17.4 L10.6 18.5 L7.4 20.5 Z" fill="#e10600" stroke="#ffd200" stroke-width="0.6"/>
    <path d="M27.8 19.5 L23.5 14.2 L18.2 15.2 L16.8 17.4 L21.4 18.5 L24.6 20.5 Z" fill="#e10600" stroke="#ffd200" stroke-width="0.6"/>
  </svg>`,

  mclaren: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="5.5" width="28" height="21" rx="3.5" fill="#14161c" stroke="#ff8000" stroke-width="1.5"/>
    <path d="M3 23.5 H29" stroke="#47c7fc" stroke-width="1.2" opacity="0.85"/>
    <path d="M5.5 21.2 C10.5 11.2 21.5 8.2 26.8 11.5 C28.2 12.4 27.6 15.1 24.4 17.5 C25.2 14.3 21.8 13.1 16.2 15.5 C12.4 17.1 8.8 19.3 5.5 21.2 Z" fill="#ff8000" stroke="#ffb347" stroke-width="0.5"/>
  </svg>`,

  racingbulls: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="5.5" width="28" height="21" rx="3.5" fill="#1434cb" stroke="#ffffff" stroke-width="1.6"/>
    <path d="M3 8.5 H29" stroke="#e10600" stroke-width="1.2"/>
    <path d="M6 21 L9.5 11 H15.5 C17.8 11 18.6 12.5 18 14.2 C17.5 15.6 16.3 16.2 15 16.5 L17.2 21 H14 L12.2 16.8 H10.5 L9 21 Z" fill="#ffffff"/>
    <path d="M18.5 21 L21.8 11 H26.8 C28.5 11 29 12.2 28.5 13.6 C28.1 14.6 27.2 15.2 26.2 15.5 C27.4 15.8 27.8 17 27.3 18.4 C26.7 20 25.3 21 23.2 21 Z" fill="#7dd3fc"/>
  </svg>`,

  alpine: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="5.5" width="28" height="21" rx="3.5" fill="#091a36" stroke="#0093cc" stroke-width="1.6"/>
    <path d="M6.5 22 L15.5 9.5 H19.2 L15.8 17.2 H22.8 L25.2 13 H27.5 L22.5 22 H19.2 L20.8 19.2 H13.8 L11.5 22 Z" fill="#00a8e8"/>
    <path d="M5.5 22 L12.5 12.5 H14.8 L7.8 22 Z" fill="#ff87bc"/>
    <path d="M4 23.5 H28" stroke="#ff87bc" stroke-width="1" opacity="0.8"/>
  </svg>`,

  audi: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="1.5" y="6.5" width="29" height="19" rx="3.5" fill="#111318" stroke="#f50537" stroke-width="1.6"/>
    <path d="M3 9 H29" stroke="#94a3b8" stroke-width="0.8" opacity="0.5"/>
    <circle cx="8.3" cy="16" r="3.9" fill="none" stroke="#f8fafc" stroke-width="1.8"/>
    <circle cx="13.4" cy="16" r="3.9" fill="none" stroke="#e2e8f0" stroke-width="1.8"/>
    <circle cx="18.6" cy="16" r="3.9" fill="none" stroke="#f8fafc" stroke-width="1.8"/>
    <circle cx="23.7" cy="16" r="3.9" fill="none" stroke="#f50537" stroke-width="1.8"/>
  </svg>`,

  haas: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="13.5" fill="#14161b" stroke="#e6002b" stroke-width="2.2"/>
    <circle cx="16" cy="16" r="11" fill="none" stroke="#ffffff" stroke-width="0.7" opacity="0.45"/>
    <path d="M9.5 9.5 H13.2 V14.2 H18.8 V9.5 H22.5 V22.5 H18.8 V17.5 H13.2 V22.5 H9.5 Z" fill="#f8fafc"/>
    <path d="M7.5 16 H24.5" stroke="#e6002b" stroke-width="1.6"/>
  </svg>`,

  williams: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="5.5" width="28" height="21" rx="3.5" fill="#081b4b" stroke="#1868db" stroke-width="1.6"/>
    <path d="M5.5 10.5 H9.2 L12.2 19.5 L15.2 11.5 H17.8 L20.4 19.5 L23.6 10.5 H27.2 L22.2 22.5 H18.8 L16.4 15.6 L13.8 22.5 H10.4 Z" fill="#ffffff"/>
    <path d="M5.5 10.5 H9.2 L12.2 19.5 L10.4 22.5 Z" fill="#64c4ff"/>
    <path d="M23.6 10.5 H27.2 L22.2 22.5 L20.4 19.5 Z" fill="#00a3ff"/>
  </svg>`,

  aston: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="5.5" width="28" height="21" rx="3.5" fill="#082820" stroke="#229971" stroke-width="1.6"/>
    <path d="M3.5 13.5 L12.5 13.5 L16 17 L19.5 13.5 L28.5 13.5 L25.5 18.8 L19 18.8 L16 21 L13 18.8 L6.5 18.8 Z" fill="#f8fafc"/>
    <path d="M5 15 H11.5 M20.5 15 H27" stroke="#94a3b8" stroke-width="0.7"/>
    <rect x="11.2" y="14.2" width="9.6" height="3.5" rx="1" fill="#229971" stroke="#cedc00" stroke-width="0.9"/>
  </svg>`,

  cadillac: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <path d="M5 7.5 H27 L25 22 L16 26 L7 22 Z" fill="#181b22" stroke="#d4af37" stroke-width="2"/>
    <rect x="7.2" y="9.5" width="8.4" height="5.2" fill="#d4af37"/>
    <rect x="16.4" y="9.5" width="8.4" height="5.2" fill="#e10600"/>
    <rect x="7.8" y="15.5" width="7.8" height="5.2" fill="#1e3f8f"/>
    <rect x="16.4" y="15.5" width="7.8" height="5.2" fill="#f8fafc"/>
    <path d="M16 7.5 V25.5 M5.8 15 H26.2" stroke="#111111" stroke-width="1.1"/>
  </svg>`,
};

const IMAGE_CACHE = new Map();

export function teamLogoSVG(teamId, size = 18) {
  const raw = LOGO_SVGS[teamId] || LOGO_SVGS.williams;
  return raw.replace("<svg ", `<svg width="${size}" height="${size}" class="team-logo-svg" `);
}

export function getTeamLogoImage(teamId) {
  if (IMAGE_CACHE.has(teamId)) return IMAGE_CACHE.get(teamId);
  const raw = LOGO_SVGS[teamId];
  if (!raw) return null;
  if (typeof Image === "undefined") return null;
  const img = new Image();
  img.src = "data:image/svg+xml;utf8," + encodeURIComponent(raw);
  IMAGE_CACHE.set(teamId, img);
  return img;
}

export const CUSTOM_ICON_PRESETS = [
  { id: "shield", label: "Apex Shield" },
  { id: "koenigsegg", label: "Koenigsegg" },
  { id: "toyota", label: "Toyota" },
  { id: "bugatti", label: "Bugatti" },
  { id: "pagani", label: "Pagani" },
  { id: "yangwang", label: "Yangwang" },
  { id: "porsche", label: "Porsche" },
  { id: "lamborghini", label: "Lamborghini" },
  { id: "maserati", label: "Maserati" },
  { id: "genesis", label: "Genesis" },
];

export function renderCustomIconSVG(iconId = "shield", code = "F1", primary = "#00d2be", secondary = "#ffffff") {
  const safeCode = String(code || "F1").toUpperCase().slice(0, 3).replace(/[^A-Z0-9]/g, "") || "F1";
  const p = /^#[0-9a-fA-F]{6}$/.test(String(primary)) ? primary : "#00d2be";
  const s = /^#[0-9a-fA-F]{6}$/.test(String(secondary)) ? secondary : "#ffffff";
  switch (iconId) {
    case "koenigsegg":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <path d="M16 2.5 L27.5 6.8 V17.2 C27.5 24 21.8 28 16 30 C10.2 28 4.5 24 4.5 17.2 V6.8 Z" fill="#12141b" stroke="#f5c451" stroke-width="1.8"/>
        <path d="M16 4.5 L25.4 8 V17 C25.4 22.6 20.8 26 16 27.8 C11.2 26 6.6 22.6 6.6 17 V8 Z" fill="${p}" stroke="${s}" stroke-width="0.8"/>
        <path d="M9.2 10.2 H22.8 V12.5 H9.2 Z" fill="#ce2b37"/>
        <path d="M16 8.5 L21.8 15.2 L16 24.2 L10.2 15.2 Z" fill="#f8fafc" stroke="#f5c451" stroke-width="0.9"/>
        <circle cx="13.8" cy="14.5" r="1.4" fill="#111827"/>
        <circle cx="18.2" cy="14.5" r="1.4" fill="#111827"/>
        <path d="M13.2 18.6 Q16 20.6 18.8 18.6" stroke="#ce2b37" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </svg>`;
    case "toyota":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="14" fill="#11141c" stroke="#eb0a1e" stroke-width="1.8"/>
        <circle cx="16" cy="16" r="12" fill="${p}" opacity="0.22"/>
        <ellipse cx="16" cy="16" rx="11.2" ry="7.4" fill="none" stroke="#f1f5f9" stroke-width="2.1"/>
        <ellipse cx="16" cy="12.9" rx="6.4" ry="3.2" fill="none" stroke="#eb0a1e" stroke-width="1.9"/>
        <ellipse cx="16" cy="16" rx="3.0" ry="7.4" fill="none" stroke="#f8fafc" stroke-width="1.9"/>
        <circle cx="16" cy="12.9" r="1.1" fill="${s}"/>
      </svg>`;
    case "bugatti":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <ellipse cx="16" cy="16" rx="14" ry="10.2" fill="#e10600" stroke="#f8fafc" stroke-width="1.8"/>
        <ellipse cx="16" cy="16" rx="12" ry="8.2" fill="none" stroke="#f8fafc" stroke-width="1.3" stroke-dasharray="1.3 1.4"/>
        <ellipse cx="16" cy="16" rx="10.2" ry="6.6" fill="#0b1f4b" stroke="#d4af37" stroke-width="0.9"/>
        <text x="16" y="19.6" text-anchor="middle" font-family="Georgia,serif" font-weight="900" font-size="10.2" fill="#ffffff" stroke="${p}" stroke-width="0.3">EB</text>
      </svg>`;
    case "pagani":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <ellipse cx="16" cy="16" rx="14" ry="9.8" fill="#151822" stroke="#cbd5e1" stroke-width="1.8"/>
        <ellipse cx="16" cy="16" rx="12" ry="7.8" fill="${p}" opacity="0.35" stroke="#00a8e8" stroke-width="0.9"/>
        <rect x="6" y="8.8" width="20" height="1.5" rx="0.7" fill="#009246"/>
        <rect x="6" y="21.7" width="20" height="1.5" rx="0.7" fill="#ce2b37"/>
        <ellipse cx="16" cy="16" rx="9.4" ry="5.3" fill="#0f172a" stroke="#f8fafc" stroke-width="1.4"/>
        <text x="16" y="18.6" text-anchor="middle" font-family="Arial,sans-serif" font-weight="900" font-size="7.2" fill="${s}">${safeCode}</text>
      </svg>`;
    case "yangwang":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <rect x="3.5" y="3.5" width="25" height="25" rx="6.5" fill="#0b1220" stroke="#f5c451" stroke-width="1.8"/>
        <rect x="5.5" y="5.5" width="21" height="21" rx="4.8" fill="${p}" opacity="0.28" stroke="#00e5ff" stroke-width="0.9"/>
        <path d="M8.5 10.5 H23.5 M8.5 21.5 H23.5" stroke="#f5c451" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M16 6.8 L10.8 16 H17.2 L12.8 25.2 L22.2 13.8 H15.8 Z" fill="#00e5ff" stroke="#ffffff" stroke-width="0.7"/>
      </svg>`;
    case "porsche":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <path d="M5.5 4 H26.5 V17 C26.5 23.5 16 28.8 16 28.8 C16 28.8 5.5 23.5 5.5 17 Z" fill="#f5c451" stroke="#111111" stroke-width="1.6"/>
        <path d="M6.5 5 H16 V15 H6.5 Z" fill="#d97706" opacity="0.5"/>
        <path d="M16 5 H25.5 V15 H16 Z" fill="#ce2b37"/>
        <path d="M6.5 15 H16 V26.5 C11 24 6.5 20.5 6.5 15 Z" fill="#111827"/>
        <path d="M16 15 H25.5 C25.5 20.5 21 24 16 26.5 Z" fill="#ce2b37"/>
        <path d="M16 4 V28.5 M5.5 15 H26.5" stroke="#f5c451" stroke-width="1.3"/>
        <rect x="11.5" y="10.8" width="9" height="8.4" rx="1.6" fill="#f8fafc" stroke="#111111" stroke-width="1"/>
        <text x="16" y="17.2" text-anchor="middle" font-family="Arial,sans-serif" font-weight="900" font-size="5.5" fill="#111111">${safeCode}</text>
      </svg>`;
    case "lamborghini":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <path d="M5.5 4.5 H26.5 L24.2 22.2 L16 28.5 L7.8 22.2 Z" fill="#111318" stroke="#f5c451" stroke-width="2"/>
        <path d="M7.5 6.5 H24.5 L22.6 20.8 L16 26 L9.4 20.8 Z" fill="${p}" opacity="0.25"/>
        <path d="M10 11.5 L16 8 L22 11.5 L20.2 19.2 L16 23.2 L11.8 19.2 Z" fill="#f5c451" stroke="#b45309" stroke-width="0.8"/>
        <path d="M12.5 12.2 L16 10.2 L19.5 12.2" stroke="#111111" stroke-width="1.4" fill="none" stroke-linecap="round"/>
        <text x="16" y="18.6" text-anchor="middle" font-family="Arial,sans-serif" font-weight="900" font-size="6.4" fill="#111111">${safeCode}</text>
      </svg>`;
    case "maserati":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <ellipse cx="16" cy="16" rx="11.5" ry="14" fill="#0b1f4b" stroke="#f8fafc" stroke-width="1.8"/>
        <ellipse cx="16" cy="16" rx="9.5" ry="12" fill="none" stroke="#e10600" stroke-width="1.1"/>
        <path d="M16 6.5 V24.5 M10.8 9.8 V15.2 Q10.8 18.4 16 18.4 Q21.2 18.4 21.2 15.2 V9.8" stroke="#f8fafc" stroke-width="2.2" fill="none" stroke-linecap="round"/>
        <path d="M13 21.5 H19" stroke="#e10600" stroke-width="1.8" stroke-linecap="round"/>
      </svg>`;
    case "genesis":
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="13.5" fill="#11141c" stroke="#d4af37" stroke-width="1.7"/>
        <path d="M3.5 12.5 L13 15.5 L3.5 18.5 M28.5 12.5 L19 15.5 L28.5 18.5" stroke="#f8fafc" stroke-width="2.1" fill="none" stroke-linecap="round"/>
        <path d="M5 14.5 L12.5 16.5 M27 14.5 L19.5 16.5" stroke="#d4af37" stroke-width="1" stroke-linecap="round"/>
        <path d="M16 9.5 L21.5 16 L16 22.5 L10.5 16 Z" fill="${p}" stroke="#d4af37" stroke-width="1.3"/>
        <circle cx="16" cy="16" r="2.2" fill="${s}"/>
      </svg>`;
    case "shield":
    default:
      return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <path d="M5 5.5 H27 L24.5 22.2 L16 28 L7.5 22.2 Z" fill="${p}" stroke="${s}" stroke-width="2"/>
        <path d="M7.2 7.5 H24.8 L22.8 20.8 L16 25.5 L9.2 20.8 Z" fill="none" stroke="#f5c451" stroke-width="0.9" opacity="0.85"/>
        <path d="M9 10.5 L23 10.5 L21.2 13.8 L10.8 13.8 Z" fill="#e10600"/>
        <text x="16" y="21.5" text-anchor="middle" font-family="Arial,sans-serif" font-weight="900" font-size="8.2" fill="${s}">${safeCode}</text>
      </svg>`;
  }
}

export function registerCustomTeamLogo(teamId, code = "F1", primary = "#00d2be", secondary = "#ffffff", iconId = "shield") {
  if (!teamId) return;
  LOGO_SVGS[teamId] = renderCustomIconSVG(iconId, code, primary, secondary);
  IMAGE_CACHE.delete(teamId);
  getTeamLogoImage(teamId);
}

// Pre-warm all 11 Constructor logo images on module load
Object.keys(LOGO_SVGS).forEach((tid) => getTeamLogoImage(tid));

