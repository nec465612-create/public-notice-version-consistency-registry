import { createProviderRegistry, getWriteClient, shortAddress } from "./wallet.js";

const SDK_URL = "https://esm.sh/genlayer-js@1.1.8?bundle";
const CHAINS_URL = "https://esm.sh/genlayer-js@1.1.8/chains?bundle";
const TYPES_URL = "https://esm.sh/genlayer-js@1.1.8/types?bundle";
const registry = createProviderRegistry();
const state = { provider: null, wallet: null, account: "", readClient: null, writeClient: null, cleanup: null, busy: false };
const ASSESSED_OUTCOMES = new Set(["CONSISTENT", "CONFLICTING", "MISSING_VERSION", "UNRESOLVED"]);
let sdkPromise;

const $ = (id) => document.getElementById(id);
const setStatus = (message, kind = "info") => {
  const node = $("status");
  node.textContent = message;
  node.dataset.kind = kind;
};
const setBusy = (busy) => {
  state.busy = busy;
  document.querySelectorAll("button").forEach((button) => { button.disabled = busy; });
};

function requireAddress() {
  const address = $("contractAddress").value.trim();
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) throw new Error("Enter the deployed Studionet contract address first.");
  return address;
}

async function ensureNetwork(provider, network) {
  const chainId = `0x${Number(network.id).toString(16)}`;
  const currentChainId = await provider.request({ method: "eth_chainId" });
  if (String(currentChainId).toLowerCase() === chainId) return;
  const chainParams = {
    chainId,
    chainName: network.name,
    rpcUrls: network.rpcUrls.default.http,
    nativeCurrency: network.nativeCurrency,
    blockExplorerUrls: [network.blockExplorers?.default.url],
  };
  try {
    await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId }] });
  } catch (error) {
    if (error?.code !== 4902) throw error;
    await provider.request({ method: "wallet_addEthereumChain", params: [chainParams] });
    await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId }] });
  }
}

async function sdk() {
  if (!sdkPromise) {
    sdkPromise = Promise.all([import(SDK_URL), import(CHAINS_URL), import(TYPES_URL)]).then(([core, chains, types]) => ({
      createClient: core.createClient,
      studionet: chains.studionet,
      TransactionStatus: types.TransactionStatus,
      ExecutionResult: types.ExecutionResult,
    }));
  }
  return sdkPromise;
}

async function clients() {
  const modules = await sdk();
  if (!state.account || !state.provider) throw new Error("Connect a wallet before using a write action.");
  state.writeClient ||= modules.createClient({
    chain: modules.studionet,
    account: state.account,
    provider: state.provider,
  });
  return modules;
}

function assertSuccess(receipt, modules) {
  const status = receipt?.statusName ?? receipt?.status;
  if (status !== modules.TransactionStatus.FINALIZED && status !== "FINALIZED" && status !== 7) {
    throw new Error(`Transaction did not reach FINALIZED (received ${status || "unknown"}).`);
  }
  const executionResult = receipt?.txExecutionResultName
    ?? receipt?.txExecutionResult
    ?? receipt?.tx_execution_result_name
    ?? receipt?.tx_execution_result;
  if (executionResult !== modules.ExecutionResult.FINISHED_WITH_RETURN && executionResult !== "FINISHED_WITH_RETURN" && executionResult !== 1) {
    throw new Error(`Finalized transaction did not report FINISHED_WITH_RETURN (received ${executionResult || "unknown"}).`);
  }
}

async function write(functionName, args) {
  const address = requireAddress();
  const modules = await clients();
  state.readClient ||= modules.createClient({ chain: modules.studionet });
  await ensureNetwork(state.provider, modules.studionet);
  const writeClient = getWriteClient(state, modules);
  const hash = await writeClient.writeContract({ address, functionName, args, value: BigInt(0) });
  setStatus(`Submitted ${hash.slice(0, 12)}… — waiting for FINALIZED`, "pending");
  const receipt = await state.readClient.waitForTransactionReceipt({
    hash,
    status: modules.TransactionStatus.FINALIZED,
    interval: 5_000,
    retries: 24,
  });
  const transaction = await state.readClient.getTransaction({ hash });
  assertSuccess({ ...receipt, ...transaction }, modules);
  return { address, hash, receipt };
}

async function readResult(caseId = $("lookupCase").value.trim()) {
  const address = requireAddress();
  const modules = await sdk();
  state.readClient ||= modules.createClient({ chain: modules.studionet });
  return state.readClient.readContract({ address, functionName: "get_result", args: [caseId] });
}

function showResult(raw) {
  const value = typeof raw === "string" ? JSON.parse(raw) : raw;
  $("resultJson").textContent = JSON.stringify(value, null, 2);
  $("resultCard").hidden = false;
  const badge = $("outcomeBadge");
  badge.textContent = value.outcome || "UNRESOLVED";
  badge.dataset.outcome = value.outcome || "UNRESOLVED";
}

function validateReadback(raw, expectedState) {
  const value = typeof raw === "string" ? JSON.parse(raw) : raw;
  if (!value || value.state !== expectedState || !ASSESSED_OUTCOMES.has(value.outcome)) {
    throw new Error(`Authoritative readback did not confirm ${expectedState}.`);
  }
  return value;
}

function formArgs() {
  const fieldIds = [
    "caseId", "subjectId", "urlA", "urlB", "noticeIdA", "noticeIdB", "revisionA", "revisionB",
    "effectiveDateA", "effectiveDateB", "retrievedBefore", "retrievedAfter",
  ];
  return fieldIds.map((id) => $(id).value.trim());
}

async function action(fn, readCaseId = null, expectedState) {
  if (state.busy) return;
  setBusy(true);
  try {
    const { hash } = await fn();
    const raw = await readResult(readCaseId || undefined);
    showResult(validateReadback(raw, expectedState));
    setStatus(`FINALIZED + SUCCESS: ${hash.slice(0, 12)}…`, "success");
  } catch (error) {
    setStatus(error?.message || String(error), "error");
  } finally {
    setBusy(false);
  }
}

function renderWalletOptions() {
  const list = $("walletOptions");
  const options = registry.list();
  list.innerHTML = "";
  if (!options.length) {
    list.innerHTML = '<p class="empty">No supported provider announced. Install MetaMask, OKX Wallet, or Rabby, then reload.</p>';
    return;
  }
  options.forEach((option) => {
    const button = document.createElement("button");
    button.className = "wallet-option";
    button.type = "button";
    button.textContent = option.label;
    button.addEventListener("click", () => connect(option));
    list.append(button);
  });
}

async function connect(option) {
  try {
    const accounts = await option.provider.request({ method: "eth_requestAccounts" });
    const account = accounts?.[0];
    if (!account) throw new Error("The selected wallet returned no account.");
    state.cleanup?.();
    state.provider = option.provider;
    state.wallet = option;
    state.account = account;
    state.writeClient = null;
    const modules = await sdk();
    state.writeClient = modules.createClient({ chain: modules.studionet, account, provider: option.provider });
    await ensureNetwork(option.provider, modules.studionet);
    const onAccountsChanged = (next) => {
      state.account = next?.[0] || "";
      state.writeClient = null;
      updateWalletUi();
    };
    const onChainChanged = () => {
      state.writeClient = null;
      setStatus("Network changed. Reconnect to validate Studionet.", "error");
    };
    option.provider.on?.("accountsChanged", onAccountsChanged);
    option.provider.on?.("chainChanged", onChainChanged);
    state.cleanup = () => {
      option.provider.removeListener?.("accountsChanged", onAccountsChanged);
      option.provider.removeListener?.("chainChanged", onChainChanged);
    };
    $("walletDialog").close();
    updateWalletUi();
    setStatus(`Connected with ${option.label} · ${shortAddress(account)}`, "success");
  } catch (error) {
    $("walletError").textContent = error?.message || String(error);
  }
}

function updateWalletUi() {
  $("walletButton").textContent = state.account ? `Connected · ${shortAddress(state.account)}` : "Connect wallet";
  $("walletState").textContent = state.account ? `${state.wallet?.label} · ${state.account}` : "Disconnected — choose a provider to continue";
  $("walletState").dataset.connected = String(Boolean(state.account));
}

window.addEventListener("eip6963:announceProvider", (event) => {
  registry.announce(event.detail);
});
window.dispatchEvent(new Event("eip6963:requestProvider"));
$("walletButton").addEventListener("click", () => {
  renderWalletOptions();
  $("walletDialog").showModal();
});
$("walletDialog").addEventListener("close", () => { $("walletError").textContent = ""; });
$("closeWallet").addEventListener("click", () => $("walletDialog").close());
$("createForm").addEventListener("submit", (event) => {
  event.preventDefault();
  action(() => write("create_case", formArgs()), $("caseId").value.trim(), "DRAFT");
});
$("freezeButton").addEventListener("click", () => action(() => write("freeze_case", [$("lookupCase").value.trim()]), null, "FROZEN"));
$("assessButton").addEventListener("click", () => action(() => write("assess", [$("lookupCase").value.trim()]), null, "ASSESSED"));
$("retryButton").addEventListener("click", () => action(() => write("retry_unresolved", [$("lookupCase").value.trim()]), null, "ASSESSED"));
$("readButton").addEventListener("click", async () => {
  try { setBusy(true); showResult(await readResult()); setStatus("Authoritative readback complete.", "success"); }
  catch (error) { setStatus(error?.message || String(error), "error"); }
  finally { setBusy(false); }
});
updateWalletUi();
