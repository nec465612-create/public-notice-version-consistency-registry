# Notice Ledger

Notice Ledger is a `PROJECT` submission for comparing two public-notice sources through a real GenLayer Intelligent Contract. A publisher or observer freezes the source provenance; validators independently fetch both HTTPS URLs and the contract stores only a consensus-backed outcome.

## Workflow

1. Deploy `contracts/notice_registry.py` to Studionet after the governed `PRE_DEPLOY` checkpoint.
2. Enter the deployed contract address in the app.
3. Connect explicitly with MetaMask, OKX Wallet, or Rabby.
4. Create a draft with source-specific notice ID, revision, effective date, and retrieval window.
5. Freeze the draft, assess both sources, and use the authoritative readback after a finalized successful transaction.

The contract never accepts a caller-supplied expected date as truth. Each source must return a bounded JSON document with `notice_id`, `revision`, `effective_date`, and `content`, or an HTML page exposing the first three values through `data-notice-id`, `data-revision`, and `data-effective-date`. A missing revision becomes `MISSING_VERSION`; unavailable, malformed, overlong, or provenance-mismatched evidence becomes `UNRESOLVED`; equal normalized content digests become `CONSISTENT`; different digests become `CONFLICTING`.

## Local verification

```powershell
genvm-lint check contracts/feasibility_probe.py --json
genvm-lint check contracts/notice_registry.py --json
pytest tests/direct -v
npm run check:frontend
node tests/frontend/wallet.test.mjs
```

The current verified environment is Python 3.13.6 with `genlayer-test==0.29.2`, `genvm-linter==0.11.0`, `genlayer-py==0.16.3`, Node 22, and GenLayerJS 1.1.8 for the browser client. The frontend waits for `FINALIZED`, requires `FINISHED_WITH_RETURN`, then performs a readback. It does not treat a submitted hash or `ACCEPTED` receipt as success.

## Scope boundary

This is a non-economic single-contract registry. It does not claim payment, escrow, staking, appeals, or real-world value. Deployment, live Studio E2E, GitHub/Vercel release, user-run exact-release E2E, and final anonymous dual approval remain governed release checkpoints.
