import assert from "node:assert/strict";
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

const legacy = registry.addLegacy({ request: async () => [] });
assert.equal(legacy.label, "Detected supported wallet");
assert.equal(registry.list().length, 3);

console.log("wallet selector checks: PASS");
