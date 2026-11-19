from tracex.providers.esplora import EsploraProvider
from tracex.providers.etherscan import EtherscanProvider


def test_esplora_parse():
    j = {"txid": "ab" * 32, "fee": 500, "status": {"confirmed": True, "block_height": 10, "block_time": 1700000000},
         "vin": [{"prevout": {"scriptpubkey_address": "bc1qin", "value": 10_000}}],
         "vout": [{"scriptpubkey_address": "bc1qout", "value": 9_500}, {"scriptpubkey": "6a00", "value": 0}]}
    tx = EsploraProvider._parse(j)
    assert tx.inputs[0].address == "bc1qin" and tx.outputs[0].value == 9_500
    assert len(tx.outputs) == 1 and tx.fee == 500 and tx.timestamp == 1700000000   # OP_RETURN skipped


def test_esplora_coinbase():
    j = {"txid": "cd" * 32, "status": {}, "vin": [{"is_coinbase": True}],
         "vout": [{"scriptpubkey_address": "bc1qminer", "value": 625000000}]}
    tx = EsploraProvider._parse(j)
    assert tx.coinbase and tx.inputs == []


def test_etherscan_mapping():
    r = {"hash": "0x1", "from": "0xAA", "to": "0xBB", "value": "1000", "timeStamp": "1700000000", "blockNumber": "5",
         "gasUsed": "21000", "gasPrice": "2", "isError": "0"}
    tx = EtherscanProvider._mk(r, "0x1")
    assert tx.inputs[0].address == "0xaa" and tx.fee == 42000
    assert EtherscanProvider._mk({**r, "isError": "1"}, "0x1") is None
    assert EtherscanProvider._mk({**r, "value": "0"}, "0x1") is None
