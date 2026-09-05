import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createProviderRegistry, getWriteClient, walletBrand } from "../../frontend/wallet.js";

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
const recreateIndex = app.indexOf("const writeClient = getWriteClient(state, modules)", networkIndex);
const writeIndex = app.indexOf("await writeClient.writeContract", recreateIndex);
assert.ok(networkIndex >= 0 && networkIndex < recreateIndex && recreateIndex < writeIndex);
assert.match(app, /const onChainChanged = \(\) => \{[\s\S]*?state\.writeClient = null;/);
const writeState = { writeClient: null, account: "0x0000000000000000000000000000000000000001", provider: providerA };
let createdClients = 0;
const writeModules = {
  studionet: { id: 61999 },
  createClient: (options) => { createdClients += 1; return { options, writeContract: async () => "0xwrite" }; },
};
writeState.writeClient = getWriteClient(writeState, writeModules);
const onChainChanged = () => { writeState.writeClient = null; };
onChainChanged();
const recoveredClient = getWriteClient(writeState, writeModules);
assert.equal(await recoveredClient.writeContract(), "0xwrite");
assert.equal(createdClients, 2);
assert.equal(app.includes("readClient ||= modules.createClient"), true);
assert.equal(app.includes("readResult(readCaseId || undefined)"), true);
assert.ok(app.indexOf("showResult(validateReadback(raw, expectedState, previousRetryCount))") < app.indexOf("setStatus(`FINALIZED + SUCCESS"));
assert.match(app, /const previousRetryCount = verifyRetry[\s\S]*?validateReadback\(await readResult\(readCaseId \|\| undefined\), expectedState\)\.retry_count/);
assert.match(app, /value\.retry_count !== previousRetryCount \+ 1/);
assert.match(app, /Authoritative readback did not confirm retry execution/);
assert.match(app, /write\("retry_unresolved"[\s\S]*?"ASSESSED", true\)/);
const validateReadbackSource = app.match(/function validateReadback\([\s\S]*?\n\}/)?.[0];
assert.ok(validateReadbackSource);
const validateReadback = new Function(
  "ASSESSED_OUTCOMES",
  `${validateReadbackSource}; return validateReadback;`,
)(new Set(["CONSISTENT", "CONFLICTING", "MISSING_VERSION", "UNRESOLVED"]));
assert.throws(
  () => validateReadback({ state: "ASSESSED", outcome: "UNRESOLVED", retry_count: 1 }, "ASSESSED", 1),
  /did not confirm retry execution/,
);
assert.equal(
  validateReadback({ state: "ASSESSED", outcome: "UNRESOLVED", retry_count: 2 }, "ASSESSED", 1).retry_count,
  2,
);
assert.match(app, /statusName \?\? receipt\?\.status/);
assert.match(app, /status !== 7/);
assert.ok(app.includes("receipt?.txExecutionResultName\n    ?? receipt?.txExecutionResult"));
assert.match(app, /tx_execution_result_name/);
assert.match(app, /if \(executionResult == null\) return/);
assert.match(app, /executionResult !== 1/);
assert.match(app, /state\.readClient\.getTransaction\(\{ hash \}\)/);

console.log("wallet selector, OKX compatibility, chain-change write, and numeric receipt checks: PASS");
