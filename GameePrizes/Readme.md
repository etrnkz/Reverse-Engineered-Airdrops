# GameePrizes

Guest-mode scripts for the Gamee / Prizes Android app API (`https://api.gamee.com/`, JSON-RPC 2.0).

## Requirements

- Python 3 (standard library only, no installs)

## Use

```bash
python gamee_client.py
```

Registers a guest account, claims the daily check-in, spins the wheel,
then submits one demo gameplay. Prints balance at the end.

```bash
python enumerate_accounts.py
```

Scans public account data (balances, levels, gameplays, countries).

The `test_*.py` files are standalone single-call examples. Replace
`YOUR_TOKEN_HERE` and `YOUR_INSTALL_UUID_HERE` with your own values
before running them.
