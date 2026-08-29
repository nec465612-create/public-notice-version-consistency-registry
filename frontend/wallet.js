const BRAND_RULES = [
  { key: "metamask", label: "MetaMask", rdns: /(^|\.)metamask(\.|$)/i, name: /metamask/i },
  { key: "okx", label: "OKX Wallet", rdns: /(^|\.)okx|okex/i, name: /okx/i },
  { key: "rabby", label: "Rabby", rdns: /(^|\.)rabby(\.|$)/i, name: /rabby/i },
];

export function walletBrand(info = {}) {
  const rdns = String(info.rdns || "");
  const name = String(info.name || "");
  return BRAND_RULES.find((rule) => rule.rdns.test(rdns) || rule.name.test(name)) || null;
}

export function createProviderRegistry() {
  const byUuid = new Map();
  const byProvider = new Map();

  function announce(detail) {
    const info = detail?.info || {};
    const provider = detail?.provider;
    const brand = walletBrand(info);
    if (!provider || typeof provider.request !== "function" || !brand) return null;
    const uuid = String(info.uuid || "");
    const existing = byProvider.get(provider) || (uuid && byUuid.get(uuid));
    if (existing && existing.provider !== provider) byProvider.delete(existing.provider);
    const record = {
      ...existing,
      key: brand.key,
      label: brand.label,
      info,
      provider,
      uuid: uuid || existing?.uuid || `${brand.key}-legacy`,
      legacy: false,
    };
    byProvider.set(provider, record);
    if (record.uuid) byUuid.set(record.uuid, record);
    for (const [candidate, value] of byProvider) {
      if (value.legacy) {
        byProvider.delete(candidate);
        byUuid.delete(value.uuid);
      }
    }
    return record;
  }

  function addLegacy(provider) {
    if (!provider || typeof provider.request !== "function") return null;
    const record = {
      key: "legacy",
      label: "Detected supported wallet",
      info: { uuid: "legacy-window-ethereum", name: "Detected supported wallet", rdns: "legacy" },
      provider,
      uuid: "legacy-window-ethereum",
      legacy: true,
    };
    byProvider.set(provider, record);
    byUuid.set(record.uuid, record);
    return record;
  }

  return {
    announce,
    addLegacy,
    list: () => [...byProvider.values()],
  };
}

export function shortAddress(address) {
  const value = String(address || "");
  return value.length > 12 ? `${value.slice(0, 6)}…${value.slice(-4)}` : value;
}
