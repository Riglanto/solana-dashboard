# Solana Ecosystem Report

_Generated 2026-11-09 11:49:57 UTC · [dashboard](dashboard.html) · [machine-readable JSON](latest.json)_

## Executive summary

As of the latest cycle, the network was in **epoch 1,081** (72.87% through); processing ~**1,102.1 tx/s**; at **211 ms** average slot time; SOL traded at **$86.17**; DeFi: TVL **$5.07B**, 24h DEX volume **$1.80B**, stablecoin supply **$15.04B**; validators: **663 active**, 34 delinquent (0.13% of stake).

## What changed

### Metrics — since 2026-11-08 10:35:06 UTC

| Metric | Before | After | Δ |
| --- | --- | --- | --- |
| TPS (latest) | 954.0 | 1,102.1 | +15.5% |
| TPS (5-sample avg) | 941.2 | 1,190.4 | +26.5% |
| Avg slot time | 214 ms | 211 ms | -1.4% |
| Epoch | 1,080 | 1,081 | +1 |
| Current slot | 466,883,397 | 467,306,791 | +423,394 |
| Epoch progress | 74.86% | 72.87% | -1.99 pp |
| Active validators | 662 | 663 | +1 |
| Delinquent validators | 35 | 34 | -1 |
| Solana TVL | $5.21B | $5.07B | -2.6% |
| DEX volume (24h) | $1.91B | $1.80B | -5.5% |
| Stablecoin supply | $14.85B | $15.04B | +1.2% |
| SOL price | $88.96 | $86.17 | -3.1% |
| Alpenglow repo stars | — | 147 | first measurement |

### Governance — since 2026-11-08 10:35:06 UTC

- **simd 0525 status**: `unavailable` → `Activated`

- **alpenglow**: `status unavailable` → `Active development (open source)`

## Network

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Current slot** | 467,306,791 | — | solana-rpc |
| **Epoch** | 1,081 | — | solana-rpc |
| **Epoch progress** | 72.87% | % | solana-rpc |
| **TPS (latest)** | 1,102.1 | — | solana-rpc |
| **TPS (5-sample avg)** | 1,190.4 | — | solana-rpc |
| **Avg slot time** | 211 ms | ms | solana-rpc |

## Validators

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Active validators** | 663 | — | solana-rpc |
| **Delinquent validators** | 34 | — | solana-rpc |
| **Total stake** | 433.92M SOL | SOL | solana-rpc |
| **Delinquent stake** | 0.13% | % | solana-rpc |

## Market

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **SOL price** | $86.17 | USD | coingecko |

## DeFi

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Solana TVL** | $5.07B | USD | defillama |
| **DEX volume (24h)** | $1.80B | USD | defillama |
| **Stablecoin supply** | $15.04B | USD | defillama |

## On-chain

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Active wallets (24h)** | — | — | unavailable |
| **Fee revenue (24h)** | — | USD | unavailable |

## Upgrades

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Alpenglow repo stars** | 147 | — | github.com/anza-xyz/alpenglow |

## Upgrades & governance

| Item | Status | Tracked from |
| --- | --- | --- |
| SIMD-0525 | SIMD-0525 Reduce Slot Times | state snapshot |
| SIMD-0525 status | Activated | state snapshot |
| SIMD-0525 created | 2026-05-01 | state snapshot |
| Alpenglow (consensus) | Active development (open source) | state snapshot |
| Alpenglow last push | 2026-08-10 | state snapshot |
| Alpenglow repo stars | 147 | github.com/anza-xyz/alpenglow |

## Sources & methodology

- **Solana RPC** (public mainnet `api.mainnet-beta.solana.com`): `getSlot`,
  `getEpochInfo`, `getVoteAccounts`, `getRecentPerformanceSamples`. TPS =
  `numTransactions / samplePeriodSecs`; slot time = `samplePeriodSecs /
  numSlots`; epoch progress = `slotIndex / slotsInEpoch`.
- **DeFiLlama**: `/v2/chains` (TVL), `/overview/dexs` (DEX volume, protocols
  listing Solana), `stablecoins` (chain circulating supply).
- **CoinGecko**: `simple/price` (SOL spot), `market_chart` (90-day history).
- **GitHub API**: SIMD proposals frontmatter; `anza-xyz/alpenglow` metadata.
- **Dune Analytics** (optional): on-chain activity metrics (active wallets,
  fee revenue) from user-configured queries. Requires a free Dune API key
  (`DUNE_API_KEY`) and a query map (`DUNE_QUERIES`); rows stay unavailable
  while unconfigured. See the README for activation.
- **Cadence**: nightly at 03:23 UTC via GitHub Actions; the repo commits
  regenerated artifacts every cycle. Every metric's definition, source, and
  collection time is embedded in `latest.json`.

## Metric definitions (appendix)

| Key | Metric | Definition | Category |
| --- | --- | --- | --- |
| network.current_slot | Current slot | Latest confirmed slot from getSlot (RPC). | Network |
| network.epoch | Epoch | Current epoch number from getEpochInfo. | Network |
| network.epoch_progress_pct | Epoch progress | slotIndex / slotsInEpoch * 100 from getEpochInfo. | Network |
| network.tps | TPS (latest) | numTransactions / samplePeriodSecs of the most recent getRecentPerformanceSamples entry. | Network |
| network.tps_avg_5 | TPS (5-sample avg) | Sum of numTransactions over sum of samplePeriodSecs across the last 5 performance samples. | Network |
| network.avg_slot_time_ms | Avg slot time | samplePeriodSecs / numSlots * 1000 from the most recent performance sample. | Network |
| validators.active_count | Active validators | Count of active vote accounts from getVoteAccounts. | Validators |
| validators.delinquent_count | Delinquent validators | Count of delinquent vote accounts from getVoteAccounts. | Validators |
| validators.total_stake_sol | Total stake | Sum of stake (active + delinquent) in SOL from getVoteAccounts. | Validators |
| validators.delinquent_stake_pct | Delinquent stake | Delinquent stake / total stake * 100. | Validators |
| market.sol_price_usd | SOL price | USD spot price from CoinGecko simple/price. | Market |
| defi.solana_tvl_usd | Solana TVL | Total value locked on Solana from DefiLlama /v2/chains. | DeFi |
| defi.dex_volume_24h_usd | DEX volume (24h) | Sum of totalVolume24h across Solana DEXes from DefiLlama /overview/dexs. | DeFi |
| defi.stablecoin_supply_usd | Stablecoin supply | Sum of peggedUSD balances on Solana from DefiLlama stablecoins. | DeFi |
| dune.active_wallets_24h | Active wallets (24h) | Distinct wallet addresses active on Solana in the last 24h, from a Dune Analytics query. Requires DUNE_API_KEY + DUNE_QUERIES; unavailable while unconfigured. | On-chain |
| dune.fee_revenue_24h_usd | Fee revenue (24h) | Total user fees paid on Solana in the last 24h in USD, from a Dune Analytics query. Requires DUNE_API_KEY + DUNE_QUERIES; unavailable while unconfigured. | On-chain |
| upgrade.alpenglow_stars | Alpenglow repo stars | Stargazer count of github.com/anza-xyz/alpenglow — a proxy for interest in the Alpenglow consensus initiative. | Upgrades |
