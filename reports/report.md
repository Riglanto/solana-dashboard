# Solana Ecosystem Report

_Generated 2026-11-25 13:12:20 UTC · [dashboard](dashboard.html) · [machine-readable JSON](latest.json)_

## Executive summary

As of the latest cycle, the network was in **epoch 1,096** (66.36% through); processing ~**1,751.4 tx/s**; at **214 ms** average slot time; SOL traded at **$67.79**; DeFi: TVL **$4.48B**, 24h DEX volume **$2.09B**, stablecoin supply **$13.11B**; validators: **659 active**, 28 delinquent (0.04% of stake).

## What changed

### Metrics — since 2026-11-24 13:57:46 UTC

| Metric | Before | After | Δ |
| --- | --- | --- | --- |
| TPS (latest) | 1,700.5 | 1,751.4 | +3.0% |
| TPS (5-sample avg) | 1,998.2 | 1,853.5 | -7.2% |
| Avg slot time | 211 ms | 214 ms | +1.1% |
| Epoch | 1,095 | 1,096 | +1 |
| Current slot | 473,369,337 | 473,758,672 | +389,335 |
| Epoch progress | 76.24% | 66.36% | -9.88 pp |
| Active validators | 661 | 659 | -2 |
| Delinquent validators | 25 | 28 | +3 |
| Solana TVL | $4.60B | $4.48B | -2.6% |
| DEX volume (24h) | $2.91B | $2.09B | -28.3% |
| Stablecoin supply | $13.46B | $13.11B | -2.6% |
| SOL price | $69.88 | $67.79 | -3.0% |

## Network

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Current slot** | 473,758,672 | — | solana-rpc |
| **Epoch** | 1,096 | — | solana-rpc |
| **Epoch progress** | 66.36% | % | solana-rpc |
| **TPS (latest)** | 1,751.4 | — | solana-rpc |
| **TPS (5-sample avg)** | 1,853.5 | — | solana-rpc |
| **Avg slot time** | 214 ms | ms | solana-rpc |

## Validators

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Active validators** | 659 | — | solana-rpc |
| **Delinquent validators** | 28 | — | solana-rpc |
| **Total stake** | 424.79M SOL | SOL | solana-rpc |
| **Delinquent stake** | 0.04% | % | solana-rpc |

## Market

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **SOL price** | $67.79 | USD | coingecko |

## DeFi

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Solana TVL** | $4.48B | USD | defillama |
| **DEX volume (24h)** | $2.09B | USD | defillama |
| **Stablecoin supply** | $13.11B | USD | defillama |

## On-chain

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Active wallets (24h)** | — | — | unavailable |
| **Fee revenue (24h)** | — | USD | unavailable |

## Upgrades

| Metric | Value | Unit | Source |
| --- | --- | --- | --- |
| **Alpenglow repo stars** | — | — | unavailable |

## Upgrades & governance

| Item | Status | Tracked from |
| --- | --- | --- |
| SIMD-0525 status | unavailable | state snapshot |
| Alpenglow (consensus) | status unavailable | state snapshot |

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
