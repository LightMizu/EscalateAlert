def main() -> None:
    import asyncio
    import logging

    from .__main__ import main as run

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
