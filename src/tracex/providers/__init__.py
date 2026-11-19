from .base import Provider  # noqa: F401


def make_provider(name: str, chain: str = "btc", **kw) -> Provider:
    name = name.lower()
    if name == "demo":
        from .demo import DemoProvider
        return DemoProvider()
    if name == "esplora":
        from .esplora import EsploraProvider
        return EsploraProvider(**kw)
    if name == "etherscan":
        from .etherscan import EtherscanProvider
        return EtherscanProvider(**kw)
    raise ValueError(f"unknown provider '{name}' (choose: demo, esplora, etherscan)")
