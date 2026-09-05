# Notice Ledger Verification

## Current release

- Repository: https://github.com/nec465612-create/public-notice-version-consistency-registry
- Executable release commit: `1057732c448c575d58e8c53d9e83156e38576b71`
- Executable release tree: `cdd0300e9e5f98cdef6e1acb247039ec3a7e90fe`
- Live application: https://public-notice-version-consistency-r.vercel.app/
- Corrected production deployment: https://public-notice-version-consistency-registry-9u6fd5ylv-nec10.vercel.app/
- Network: GenLayer Studionet, chain `61999`
- Contract: [`0x0B07e2D40286E4031e916A66d2EB76Dbc0E47D12`](https://explorer-studio.genlayer.com/address/0x0B07e2D40286E4031e916A66d2EB76Dbc0E47D12)
- Deployment transaction: [`0xb8130356f974d6cc2a9f3b09df0c2e6277eb63622ea3f551e1ba38ccb70b1ceb`](https://explorer-studio.genlayer.com/tx/0xb8130356f974d6cc2a9f3b09df0c2e6277eb63622ea3f551e1ba38ccb70b1ceb)

## Source identity

| File | SHA-256 |
| --- | --- |
| `contracts/notice_registry.py` | `B236E28809826E6559878E327349248C8079F63C34E6AFE773DA9EE93760B651` |
| `frontend/app.js` | `091A954631A32D5D319896E7433F5A87149DE06E30F23FE95ACCCB8DD67EAE27` |
| `frontend/wallet.js` | `5C0826870C9AC4F612440039CD8681282ED2E3953DE1D3229EF9668B352ED992` |
| `index.html` | `86BAFB61CA085A066A6394E7DF57689BF20F0A64DDA75418CD57B08B6446DBD4` |
| `frontend/styles.css` | `274E8954030BF3F3DD729A67883B110F9E080B2A7C02E4B6F666263B47390AB8` |
| `tests/frontend/wallet.test.mjs` | `96C015924D96F14C427F0B5B57EFDC34016CEA8EDD43462D5B0A7C45DDFF159D` |
| `vercel.json` | `5687163E7CCD7D2F28D4B797B487C85DB6981A00DB7B4B77C5F56A93C7A134CC` |

The deployed contract source matches the recorded contract hash. The browser release uses the same `index.html`, `frontend/app.js`, `frontend/wallet.js`, and stylesheet hashes listed above.

## Verification commands

```text
genvm-lint check contracts/feasibility_probe.py --json  -> ok=true
genvm-lint check contracts/notice_registry.py --json    -> ok=true
pytest tests/direct -v                                  -> 25 passed
npm run check:frontend                                   -> PASS
node tests/frontend/wallet.test.mjs                     -> PASS
py -3 -m compileall -q contracts tests                 -> PASS
git diff --check                                         -> PASS
```

The linter reports only non-blocking informational diagnostic `I200` about a newer runner. The browser client is pinned to GenLayerJS `1.1.8`.

## Retry confirmation

Before `retry_unresolved`, the frontend reads and retains the authoritative `retry_count`. After the submitted transaction reaches finality and passes any available execution-result check, it reads the record again. The UI reports success only when the state remains `ASSESSED`, the outcome is valid, and `retry_count` equals the retained value plus one. An unchanged previously assessed record therefore fails with an explicit retry-verification error instead of being shown as a successful retry. The frontend regression executes both the unchanged-count rejection and incremented-count success cases.

## Live proof matrix

Every row below is a real Studionet transaction on the contract above. All successful rows finalized with successful execution and were checked by authoritative readback.

| Requirement / action | Transaction evidence | Final readback |
| --- | --- | --- |
| Create, freeze, and assess a consistent pair | [create](https://explorer-studio.genlayer.com/tx/0x65bcd023466e56fceafa0e22e56a799bf624fa4fb78509c6d249d55b0f196e0c), [freeze](https://explorer-studio.genlayer.com/tx/0x45a8d81299565b3ad7da9b0c56548da2f373a5eb6feecbd28a2a46549b98e05d), [assess](https://explorer-studio.genlayer.com/tx/0xf2fdc5475d363722186b1d554441487f3e410949a1f64286d18a240c2154de95) | `ASSESSED`, `CONSISTENT`; equal digest `2e68a7bba11b90d1bae1daea2dd4951779cf45d5897c62539d01f44054bcb1e0` |
| Assess a conflicting pair | [create](https://explorer-studio.genlayer.com/tx/0xd9823f8641037fad622a2cb9eedce535aa62de521944d605f51f9115b52f8e6e), [freeze](https://explorer-studio.genlayer.com/tx/0x1bb115ab1ded7fdb157e75e642994769897981d8ecf848ece371e0e9bba73d06), [assess](https://explorer-studio.genlayer.com/tx/0xdc781d42c502761753286c76d88a4960246a49e6a4d6f23c8209bb9ec2b59bc0) | `ASSESSED`, `CONFLICTING`; distinct source digests |
| Assess a source with no revision | [create](https://explorer-studio.genlayer.com/tx/0xb79ed002f946a8c285b6c43619bf06b64feed3bea3300830b48f213553d7f661), [freeze](https://explorer-studio.genlayer.com/tx/0x67861845ad31b8bbc43923abd73eb5f753b2bdae1e11f3d64bb5431fab539001), [assess](https://explorer-studio.genlayer.com/tx/0xef6d3b63b1906e63a978bf5b22e0d56dac2a90d6a8f08db142e3d1cc2bb875e7) | `ASSESSED`, `MISSING_VERSION` |
| Assess an unavailable source and exhaust retries | [assess](https://explorer-studio.genlayer.com/tx/0x344cfdc31c1c39856d7cd9b185ed30a79ff650263b742edb2f77987aa1db35d8), [retry 1](https://explorer-studio.genlayer.com/tx/0xf42e06b1c32a9961eebceb9e0b964a95270b54198d11af9b0f2d72cf254134e4), [retry 2](https://explorer-studio.genlayer.com/tx/0x77dd1bf7c224ac584c99d9b0ac6ffe01cab754e06c5e7bbd83cbe69f7c2a4b37), [retry 3](https://explorer-studio.genlayer.com/tx/0xd57b4b9559086db81672a5199976fc7ccd0d1b0448921c7bf24d7c2d4fb97484) | First three `FINALIZED`/`SUCCESS`; retry 3 `FINALIZED`/`ERROR` with `retry limit reached`; final `UNRESOLVED`, `retry_count=2` |
| Judge-feedback retry execution proof from a fresh OKX-owned case | [create](https://explorer-studio.genlayer.com/tx/0xb97cd143838b220e36e9bfe23ba672c61a0bb137590027ab2a532359e6de5181), [freeze](https://explorer-studio.genlayer.com/tx/0x3571268033e575d0b87239e90c057ea91781545795cd2f4649b6798f20e92161), [assess](https://explorer-studio.genlayer.com/tx/0x3afdbab7feded3d5337e1cf991da53e83123071f23aba49be8fe589a0dd7495d), [retry](https://explorer-studio.genlayer.com/tx/0x0718e279971e16609509f2aa5088cba77f571c266cab097c63882022fe5ff56a) | Case `judge-retry-proof-20260905-1605`; all four transactions `FINALIZED`/`SUCCESS` with consensus `Accepted`; authoritative state changed from `ASSESSED`, `UNRESOLVED`, `retry_count=0` before retry to `retry_count=1` after retry; a clean reload independently returned the same post-state without a connected wallet. |

The corrected exact-release journey used OKX account `0xa8c46fbc5fc7a1485acd07734241b1b4e46dd1cb` on the clean production URL. Production hashes matched the source table, the retry was accepted only after the post-transaction counter increased from `0` to `1`, and a public read after reload independently confirmed the post-state. The wallet integration uses standard injected-provider requests and does not depend on wallet Snap APIs.

## Trust boundary and limitations

- Validators fetch the two HTTPS sources inside GenLayer nondeterministic execution; the contract compares the validator-backed outcome and digest fields.
- The caller supplies provenance and a retrieval window, but cannot supply the source content or expected effective date as truth.
- Malformed, overlong, unavailable, missing-version, missing-timestamp, out-of-window, and provenance-mismatched evidence fails closed.
- This release is non-economic and has no payment, escrow, staking, appeals, or upgrade workflow.
