# Notice Ledger

Notice Ledger is a GenLayer `PROJECT` for comparing two public-notice sources through a real Intelligent Contract. A publisher or observer freezes the source provenance; validators independently fetch both HTTPS URLs and the contract stores only a consensus-backed outcome.

- Live application: https://public-notice-version-consistency-r.vercel.app/
- Studionet contract: [`0x0B07e2D40286E4031e916A66d2EB76Dbc0E47D12`](https://explorer-studio.genlayer.com/address/0x0B07e2D40286E4031e916A66d2EB76Dbc0E47D12)
- Deployment transaction: [`0xb8130356f974d6cc2a9f3b09df0c2e6277eb63622ea3f551e1ba38ccb70b1ceb`](https://explorer-studio.genlayer.com/tx/0xb8130356f974d6cc2a9f3b09df0c2e6277eb63622ea3f551e1ba38ccb70b1ceb)
- Verification: [`docs/VERIFICATION.md`](docs/VERIFICATION.md)

## Workflow

1. Enter the deployed Studionet contract address in the app.
2. Connect explicitly with MetaMask, OKX Wallet, or Rabby.
3. Create a draft with source-specific notice ID, revision, effective date, and retrieval window.
4. Freeze the draft, assess both sources, and use the authoritative readback after a finalized successful transaction.

The contract never accepts a caller-supplied expected date as truth. Each source must return a bounded JSON document with `notice_id`, `revision`, `effective_date`, `retrieved_at`, and `content`, or an HTML page exposing those values through `data-notice-id`, `data-revision`, `data-effective-date`, and `data-retrieved-at`; `Date`/`Last-Modified` headers are also accepted. The frozen retrieval window is inclusive and both source timestamps must fall inside it. A missing revision becomes `MISSING_VERSION`; unavailable, malformed, overlong, missing-timestamp, out-of-window, or provenance-mismatched evidence becomes `UNRESOLVED`; equal normalized content digests become `CONSISTENT`; different digests become `CONFLICTING`.

## Local verification

```powershell
genvm-lint check contracts/feasibility_probe.py --json
genvm-lint check contracts/notice_registry.py --json
pytest tests/direct -v
npm run check:frontend
node tests/frontend/wallet.test.mjs
```

The verified environment is Python 3.13.6 with `genlayer-test==0.29.2`, `genvm-linter==0.11.0`, `genlayer-py==0.16.3`, Node 22, and GenLayerJS 1.1.8 for the browser client. The frontend waits for `FINALIZED`, requires successful execution, then performs an authoritative readback. It does not treat a submitted hash or `ACCEPTED` receipt as success.

The final release evidence records the exact source revision, deployment parity, local checks, and live proof matrix in [`docs/VERIFICATION.md`](docs/VERIFICATION.md).

## Scope boundary

This is a non-economic single-contract registry. It does not claim payment, escrow, staking, appeals, or real-world value. Source availability, response shape, retrieval timestamps, and the configured retrieval window affect the resulting classification; unavailable or malformed evidence fails closed as `UNRESOLVED`.
