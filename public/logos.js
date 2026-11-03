// Precision Vector Constructor Emblems (Inline SVG + Pre-Rasterized Canvas Image Cache)

const LOGO_SVGS = {
  mercedes: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="13.5" fill="#0d1117" stroke="#d8dee9" stroke-width="2"/>
    <circle cx="16" cy="16" r="11" fill="none" stroke="#00d2be" stroke-width="0.9" opacity="0.85"/>
    <path d="M16 3.5 L18.1 14.3 L27.2 22.4 L16 17.8 L4.8 22.4 L13.9 14.3 Z" fill="#eef2f6"/>
    <circle cx="16" cy="16" r="1.4" fill="#94a3b8"/>
  </svg>`,

  ferrari: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <path d="M6 4 H26 V17 C26 23.8 20.8 27.8 16 29.5 C11.2 27.8 6 23.8 6 17 Z" fill="#ffd800" stroke="#111" stroke-width="1.4"/>
    <rect x="6.7" y="4.7" width="18.6" height="2.2" fill="#009246"/>
    <rect x="6.7" y="6.9" width="18.6" height="2.0" fill="#ffffff"/>
    <rect x="6.7" y="8.9" width="18.6" height="2.2" fill="#ce2b37"/>
    <path d="M16.5 12.2 C18.8 12.2 19.6 14 18.4 15.8 L20.2 18.6 L18.2 19.2 L16.8 17.2 L15.4 20.8 L17.6 22.6 H13.2 L14.1 18.4 L12.3 16.5 L14.2 14.2 C14.6 12.8 15.4 12.2 16.5 12.2 Z" fill="#111"/>
    <text x="16" y="26.4" text-anchor="middle" font-family="Arial,sans-serif" font-weight="900" font-size="5.2" fill="#111">SF</text>
  </svg>`,

  redbull: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="6" width="28" height="20" rx="3" fill="#121f45" stroke="#3671c6" stroke-width="1.5"/>
    <circle cx="16" cy="16" r="5.6" fill="#ffd200"/>
    <path d="M4.2 19.5 L8.5 14.2 L13.8 15.2 L15.2 17.4 L10.6 18.5 L7.4 20.5 Z" fill="#e10600" stroke="#ffd200" stroke-width="0.5"/>
    <path d="M27.8 19.5 L23.5 14.2 L18.2 15.2 L16.8 17.4 L21.4 18.5 L24.6 20.5 Z" fill="#e10600" stroke="#ffd200" stroke-width="0.5"/>
  </svg>`,

  mclaren: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="6" width="28" height="20" rx="3" fill="#14161c" stroke="#ff8000" stroke-width="1.3"/>
    <path d="M5.5 21.5 C10.5 11.5 21.5 8.5 26.8 11.8 C28.2 12.7 27.6 15.4 24.4 17.8 C25.2 14.6 21.8 13.4 16.2 15.8 C12.4 17.4 8.8 19.6 5.5 21.5 Z" fill="#ff8000"/>
  </svg>`,

  racingbulls: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="6" width="28" height="20" rx="3" fill="#1434cb" stroke="#ffffff" stroke-width="1.5"/>
    <path d="M6 21 L9.5 11 H15.5 C17.8 11 18.6 12.5 18 14.2 C17.5 15.6 16.3 16.2 15 16.5 L17.2 21 H14 L12.2 16.8 H10.5 L9 21 Z" fill="#ffffff"/>
    <path d="M18.5 21 L21.8 11 H26.8 C28.5 11 29 12.2 28.5 13.6 C28.1 14.6 27.2 15.2 26.2 15.5 C27.4 15.8 27.8 17 27.3 18.4 C26.7 20 25.3 21 23.2 21 Z" fill="#6692ff"/>
  </svg>`,

  alpine: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="6" width="28" height="20" rx="3" fill="#091a36" stroke="#0093cc" stroke-width="1.5"/>
    <path d="M6.5 22 L15.5 9.5 H19.2 L15.8 17.2 H22.8 L25.2 13 H27.5 L22.5 22 H19.2 L20.8 19.2 H13.8 L11.5 22 Z" fill="#0093cc"/>
    <path d="M5.5 22 L12.5 12.5 H14.8 L7.8 22 Z" fill="#ff87bc"/>
  </svg>`,

  audi: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="1.5" y="7" width="29" height="18" rx="3" fill="#121318" stroke="#f50537" stroke-width="1.4"/>
    <circle cx="8.3" cy="16" r="3.9" fill="none" stroke="#eef2f6" stroke-width="1.7"/>
    <circle cx="13.4" cy="16" r="3.9" fill="none" stroke="#eef2f6" stroke-width="1.7"/>
    <circle cx="18.6" cy="16" r="3.9" fill="none" stroke="#eef2f6" stroke-width="1.7"/>
    <circle cx="23.7" cy="16" r="3.9" fill="none" stroke="#eef2f6" stroke-width="1.7"/>
  </svg>`,

  haas: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="13" fill="#14161b" stroke="#e6002b" stroke-width="2.2"/>
    <path d="M9.5 9.5 H13.2 V14.2 H18.8 V9.5 H22.5 V22.5 H18.8 V17.5 H13.2 V22.5 H9.5 Z" fill="#f1f5f9"/>
    <path d="M7.5 16 H24.5" stroke="#e6002b" stroke-width="1.4"/>
  </svg>`,

  williams: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="6" width="28" height="20" rx="3" fill="#081b4b" stroke="#1868db" stroke-width="1.6"/>
    <path d="M5.5 10.5 H9.2 L12.2 19.5 L15.2 11.5 H17.8 L20.4 19.5 L23.6 10.5 H27.2 L22.2 22.5 H18.8 L16.4 15.6 L13.8 22.5 H10.4 Z" fill="#ffffff"/>
    <path d="M5.5 10.5 H9.2 L12.2 19.5 L10.4 22.5 Z" fill="#64c4ff"/>
  </svg>`,

  aston: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <rect x="2" y="6" width="28" height="20" rx="3" fill="#0b2e25" stroke="#229971" stroke-width="1.5"/>
    <path d="M3.5 14 L12.5 14 L16 17.5 L19.5 14 L28.5 14 L25.5 18.5 L19 18.5 L16 20.5 L13 18.5 L6.5 18.5 Z" fill="#f1f5f9"/>
    <rect x="11.5" y="14.5" width="9" height="3.2" rx="1" fill="#229971" stroke="#cedc00" stroke-width="0.6"/>
  </svg>`,

  cadillac: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
    <path d="M5 8 H27 L25 22 L16 25.5 L7 22 Z" fill="#181b22" stroke="#d4af37" stroke-width="2"/>
    <rect x="7.2" y="9.8" width="8.4" height="5.2" fill="#d4af37"/>
    <rect x="16.4" y="9.8" width="8.4" height="5.2" fill="#e10600"/>
    <rect x="7.8" y="15.8" width="7.8" height="5.2" fill="#1e3f8f"/>
    <rect x="16.4" y="15.8" width="7.8" height="5.2" fill="#d4af37"/>
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
  const img = new Image();
  img.src = "data:image/svg+xml;utf8," + encodeURIComponent(raw);
  IMAGE_CACHE.set(teamId, img);
  return img;
}

// Pre-warm all 11 Constructor logo images on module load
Object.keys(LOGO_SVGS).forEach((tid) => getTeamLogoImage(tid));

