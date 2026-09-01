"""Data source adapters.

ALL_COLLECTORS: metric collectors → list[Metric].
ALL_STATE_COLLECTORS: state collectors → (list[Metric], dict[str, str]).
"""

from solana_dashboard.collectors.coingecko import collect as collect_coingecko
from solana_dashboard.collectors.defillama import collect as collect_defillama
from solana_dashboard.collectors.dune import collect as collect_dune
from solana_dashboard.collectors.rpc import collect as collect_rpc
from solana_dashboard.collectors.solana_data import collect as collect_solana_data

ALL_COLLECTORS = {
    "rpc": collect_rpc,
    "defillama": collect_defillama,
    "coingecko": collect_coingecko,
    "dune": collect_dune,
}

ALL_STATE_COLLECTORS = {
    "solana_data": collect_solana_data,
}

__all__ = [
    "ALL_COLLECTORS",
    "ALL_STATE_COLLECTORS",
    "collect_rpc",
    "collect_defillama",
    "collect_coingecko",
    "collect_dune",
    "collect_solana_data",
]
