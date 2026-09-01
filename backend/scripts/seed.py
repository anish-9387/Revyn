"""Create the schema and generate the synthetic merchant.

Usage:
    python -m scripts.seed
    python -m scripts.seed --customers 800 --transactions 6000 --keep
"""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.config import settings
from app.core.db import SessionFactory, dispose_engine, init_models
from app.core.logging import configure_logging
from app.services import seeding


async def main(args: argparse.Namespace) -> None:
    configure_logging()
    await init_models()
    async with SessionFactory() as session:
        summary = await seeding.seed(
            session,
            reset_first=not args.keep,
            customers=args.customers,
            transactions=args.transactions,
            train_model=not args.skip_training,
        )
        await session.commit()
    await dispose_engine()
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Revyn synthetic dataset")
    parser.add_argument("--customers", type=int, default=settings.synthetic_customers)
    parser.add_argument("--transactions", type=int, default=settings.synthetic_transactions)
    parser.add_argument("--keep", action="store_true", help="append instead of resetting")
    parser.add_argument("--skip-training", action="store_true", help="do not fit the model")
    asyncio.run(main(parser.parse_args()))
