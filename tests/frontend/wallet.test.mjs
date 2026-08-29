import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createProviderRegistry, walletBrand } from "../../frontend/wallet.js";

const providerA = { request: async () => [] };
const providerB = { request: async () => [] };
const registry = createProviderRegistry();

assert.equal(walletBrand({ name: "MetaMask", rdns: "io.metamask" }).key, "metamask");
assert.equal(walletBrand({ name: "OKX Wallet", rdns: "com.okex.wallet" }).key, "okx");
assert.equal(walletBrand({ name: "Rabby", rdns: "io.rabby" }).key, "rabby");
assert.equal(walletBrand({ name: "Unknown", rdns: "unknown" }), null);

registry.announce({ info: { uuid: "a", name: "MetaMask", rdns: "io.metamask" }, provider: providerA });
registry.announce({ info: { uuid: "a", name: "MetaMask", rdns: "io.metamask" }, provider: providerA });
registry.announce({ info: { uuid: "b", name: "Rabby", rdns: "io.rabby" }, provider: providerB });
assert.equal(registry.list().length, 2);
assert.equal(registry.list()[0].label, "MetaMask");
assert.equal(registry.list()[1].label, "Rabby");
registry.announce({ info: { uuid: "b", name: "Rabby", rdns: "io.rabby" }, provider: { request: async () => [] } });
assert.equal(registry.list().length, 2);

assert.equal(typeof registry.addLegacy, "undefined");
const app = readFileSync(new URL("../../frontend/app.js", import.meta.url), "utf8");
const index = readFileSync(new URL("../../index.html", import.meta.url), "utf8");
assert.equal(app.includes("registry.addLegacy"), false);
assert.equal(app.includes("wallet_getSnaps"), false);
assert.equal(app.includes('.connect("studionet")'), false);
assert.match(app, /ensureNetwork/);
assert.match(index, /id="walletState"/);
const networkIndex = app.indexOf("await ensureNetwork(state.provider, modules.studionet)");
const recreateIndex = app.indexOf("const writeClient = state.writeClient ||= modules.createClient", networkIndex);
const writeIndex = app.indexOf("await writeClient.writeContract", recreateIndex);
assert.ok(networkIndex >= 0 && networkIndex < recreateIndex && recreateIndex < writeIndex);
assert.match(app, /const onChainChanged = \(\) => \{[\s\S]*?state\.writeClient = null;/);
assert.equal(app.includes("readClient ||= modules.createClient"), true);
assert.equal(app.includes("readResult(readCaseId || undefined)"), true);
assert.ok(app.indexOf("showResult(validateReadback(raw, expectedState))") < app.indexOf("setStatus(`FINALIZED + SUCCESS"));

console.log("wallet selector, OKX compatibility, and chain-change write checks: PASS");
