"""Populate an empty local Cartiva catalog with sample data."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Session, create_engine, select

from cartiva.backend.config import PROJECT_ROOT, get_settings
from cartiva.backend.models import Product, ProductVariant


class SeedCredentials(BaseSettings):
    """Load administrator credentials for this setup operation."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    username: str = Field(validation_alias="POSTGRES_USER")
    password: SecretStr = Field(validation_alias="POSTGRES_PASSWORD")


CATALOG = [
    {
        "name": "Everyday Shirt",
        "description": "A comfortable cotton shirt for everyday wear.",
        "category": "Shirts",
        # Each tuple contains size, color, price in cents, and stock.
        "variants": [
            ("S", "Green", 2999, 8),
            ("M", "Green", 2999, 0),
            ("L", "Green", 2999, 5),
            ("M", "Ivory", 2999, 6),
        ],
    },
    {
        "name": "Straight-Leg Jeans",
        "description": "Classic straight-leg denim with a clean finish.",
        "category": "Jeans",
        "variants": [
            ("28", "Black", 5999, 4),
            ("30", "Black", 5999, 7),
            ("30", "Blue", 5999, 3),
        ],
    },
    {
        "name": "Everyday Tote",
        "description": "A simple canvas tote for daily essentials.",
        "category": "Accessories",
        "variants": [
            ("One Size", "Ivory", 1999, 10),
        ],
    },
]


def seed_catalog() -> None:
    settings = get_settings()
    credentials = SeedCredentials()

    # Use a separate admin connection; keep the API's account unchanged.
    seed_url = settings.database_url.set(
        username=credentials.username,
        password=credentials.password.get_secret_value(),
    )

    engine = create_engine(
        seed_url,
        connect_args={"connect_timeout": 5},
        echo=False,
    )

    try:
        with Session(engine) as session:
            with session.begin():
                existing_product = session.exec(
                    select(Product.id).limit(1)
                ).first()
                existing_variant = session.exec(
                    select(ProductVariant.id).limit(1)
                ).first()

                if existing_product is not None or existing_variant is not None:
                    print("Catalog is not empty; no data changed.")
                    return

                variant_count = 0

                for item in CATALOG:
                    product = Product(
                        name=item["name"],
                        description=item["description"],
                        category=item["category"],
                    )
                    session.add(product)

                    # Send the INSERT to obtain the database-generated ID.
                    # The transaction is not committed yet.
                    session.flush()

                    for size, color, price_cents, stock in item["variants"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color,
                            price_cents=price_cents,
                            stock_quantity=stock,
                        )
                        session.add(variant)
                        variant_count += 1

            # Reaching here means the transaction committed successfully.
            print(
                f"Seed complete: {len(CATALOG)} products "
                f"and {variant_count} variants created."
            )
    finally:
        engine.dispose()


if __name__ == "__main__":
    seed_catalog()