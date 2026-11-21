"""The storefront page is served by the API alongside the JSON endpoints."""


def test_root_redirects_to_storefront(catalog_environment):
    client, _ = catalog_environment

    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/shop/"


def test_storefront_page_is_served(catalog_environment):
    client, _ = catalog_environment

    response = client.get("/shop/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CARTIVA" in response.text


def test_storefront_script_and_styles_are_served(catalog_environment):
    client, _ = catalog_environment

    assert client.get("/shop/app.js").status_code == 200
    assert client.get("/shop/styles.css").status_code == 200


def test_storefront_never_sends_prices():
    """CART-003: prices come from the server; the page must not send them."""
    from pathlib import Path

    script = (Path(__file__).resolve().parents[2]
              / "storefront" / "app.js").read_text()

    assert "price_cents:" not in script
    assert '"price_cents"' not in script
