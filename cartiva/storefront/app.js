// Cartiva storefront. Talks only to the existing API:
//   GET /products, POST /carts, POST /carts/{id}/items, GET /carts/{id},
//   PATCH and DELETE /carts/{id}/items/{item_id}.
// Prices always come from the server; the page never sends a price.

const COLOR_HEX = {
  "Beige": "#d9c7a7", "Black": "#1b1b1b", "Blue": "#3f5f8f",
  "Blue Floral": "#6f8fbf", "Brown": "#6b4a32", "Burgundy": "#6d1f2f",
  "Camel": "#b98b5a", "Champagne": "#e8d6b5", "Charcoal": "#3c3c3c",
  "Cognac": "#9a5a2c", "Cream": "#f1e9d8", "Ecru": "#ece3cf",
  "Emerald": "#1f6b52", "Green": "#4f7a4a", "Grey": "#9a9a9a",
  "Indigo": "#2e3d66", "Ivory": "#f4efe3", "Khaki": "#b5a97e",
  "Light Blue": "#a9c1db", "Navy": "#1f2a44", "Navy Print": "#2f3d63",
  "Oatmeal": "#d8ccb6", "Olive": "#6b6b3a", "Red Floral": "#b5523f",
  "Rose": "#d9a3a3", "Rust Print": "#a8552f", "Sage": "#a3b19a",
  "Sand": "#d8c6a3", "Silver": "#c0c0c0", "Sky Blue": "#9cc3e0",
  "Tan": "#c49a6c", "Taupe": "#8b7d6b", "Tortoise": "#6e4a2a",
  "White": "#fafafa",
};
const CART_KEY = "cartivaCartId";
const IMAGE_TYPES = ["jpg", "png", "webp"];

const state = {
  allProducts: [],
  category: "All",
  query: "",
  cartId: localStorage.getItem(CART_KEY),
  picks: {}, // productId -> { color, variantId }
};

const $ = (id) => document.getElementById(id);

// Build DOM elements without innerHTML, so text is never treated as HTML.
function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== false && value != null) node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) if (child) node.append(child);
  return node;
}

const money = (cents) =>
  (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });

const slug = (name) =>
  name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

function toast(message) {
  const box = $("toast");
  box.textContent = message;
  box.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (box.hidden = true), 2600);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      typeof body.detail === "string" ? body.detail : "Something went wrong"
    );
    error.status = response.status;
    throw error;
  }
  return body;
}

// ---------- Catalog ----------

async function loadCatalog() {
  state.allProducts = await api("/products");
  renderCategories();
  await renderProducts();
}

function renderCategories() {
  const names = ["All", ...new Set(state.allProducts.map((p) => p.category))];
  const nav = $("categories");
  nav.replaceChildren(
    ...names.map((name) =>
      el("button", {
        text: name,
        class: name === state.category ? "active" : "",
        onclick: () => {
          state.category = name;
          renderCategories();
          renderProducts();
        },
      })
    )
  );
}

async function renderProducts() {
  const params = new URLSearchParams();
  if (state.query) params.set("q", state.query);
  if (state.category !== "All") params.set("category", state.category);
  const products = await api(`/products?${params}`);

  // Search results include only matching variants; show the full product.
  const fullById = new Map(state.allProducts.map((p) => [p.id, p]));
  const cards = products.map((p) => productCard(fullById.get(p.id) || p));

  $("result-count").textContent = `${products.length} ${
    products.length === 1 ? "item" : "items"
  }`;
  $("grid").replaceChildren(
    ...(cards.length
      ? cards
      : [el("p", { class: "empty", text: "No products match your search." })])
  );
}

function photo(product, color) {
  const box = el("div", { class: "photo" });
  const hex = COLOR_HEX[color] || "#cfcfcf";
  const tile = el("div", {
    class: "tile",
    style: `background: linear-gradient(160deg, #f6f5f3 30%, ${hex}55)`,
  }, [
    el("span", { class: "tile-category", text: product.category }),
    el("span", { class: "tile-name", text: product.name }),
  ]);
  box.append(tile);

  // Try images/<product-slug>.jpg, .png, .webp; keep the tile if none exist.
  const img = el("img", { alt: product.name, loading: "lazy" });
  let attempt = 0;
  img.addEventListener("error", () => {
    attempt += 1;
    if (attempt < IMAGE_TYPES.length) {
      img.src = `images/${slug(product.name)}.${IMAGE_TYPES[attempt]}`;
    } else {
      img.remove();
    }
  });
  img.addEventListener("load", () => tile.remove());
  img.src = `images/${slug(product.name)}.${IMAGE_TYPES[0]}`;
  box.append(img);
  return box;
}

function productCard(product) {
  const colors = [...new Set(product.variants.map((v) => v.color))];
  const pick = state.picks[product.id] || { color: colors[0], variantId: null };
  state.picks[product.id] = pick;

  const inColor = product.variants.filter((v) => v.color === pick.color);
  const allSoldOut = product.variants.every((v) => v.stock_quantity === 0);
  const prices = product.variants.map((v) => v.price_cents);
  const price = Math.min(...prices) === Math.max(...prices)
    ? money(prices[0])
    : `from ${money(Math.min(...prices))}`;

  const rerender = () => {
    card.replaceWith(productCard(product));
  };

  const swatches = el("div", { class: "swatches" }, colors.map((color) =>
    el("button", {
      class: `swatch ${color === pick.color ? "active" : ""}`,
      style: `background: ${COLOR_HEX[color] || "#cfcfcf"}`,
      title: color,
      "aria-label": color,
      onclick: () => {
        pick.color = color;
        pick.variantId = null;
        rerender();
      },
    })
  ));

  const sizes = el("div", { class: "sizes" }, inColor.map((variant) =>
    el("button", {
      class: `size ${variant.id === pick.variantId ? "active" : ""}`,
      text: variant.size,
      disabled: variant.stock_quantity === 0,
      title: variant.stock_quantity === 0 ? "Sold out" : `${variant.stock_quantity} left`,
      onclick: () => {
        pick.variantId = variant.id;
        rerender();
      },
    })
  ));

  const addButton = el("button", {
    class: "add",
    text: pick.variantId ? "Add to bag" : "Select a size",
    disabled: !pick.variantId,
    onclick: async () => {
      addButton.disabled = true;
      try {
        await addToBag(pick.variantId);
        toast(`Added: ${product.name}, ${pick.color}`);
      } catch (error) {
        toast(error.message);
      } finally {
        addButton.disabled = false;
      }
    },
  });

  const card = el("article", { class: "card" }, [
    el("div", { style: "position: relative" }, [
      photo(product, pick.color),
      allSoldOut ? el("span", { class: "badge", text: "Sold out" }) : null,
    ]),
    el("div", { class: "card-title" }, [
      el("span", { text: product.name }),
      el("span", { class: "price", text: price }),
    ]),
    swatches,
    el("span", { class: "color-name", text: pick.color }),
    sizes,
    addButton,
  ]);
  return card;
}

// ---------- Bag ----------

async function ensureCart() {
  if (state.cartId) return state.cartId;
  const cart = await api("/carts", { method: "POST" });
  state.cartId = cart.id;
  localStorage.setItem(CART_KEY, cart.id);
  return cart.id;
}

function forgetCart() {
  state.cartId = null;
  localStorage.removeItem(CART_KEY);
}

async function addToBag(variantId) {
  const body = JSON.stringify({ variant_id: variantId, quantity: 1 });
  try {
    await api(`/carts/${await ensureCart()}/items`, { method: "POST", body });
  } catch (error) {
    // The saved cart may no longer exist (e.g. after a database reset).
    if (error.status !== 404 || error.message !== "Cart not found") throw error;
    forgetCart();
    await api(`/carts/${await ensureCart()}/items`, { method: "POST", body });
  }
  await refreshBag();
}

async function refreshBag() {
  if (!state.cartId) {
    renderBag({ items: [], subtotal_cents: 0 });
    return;
  }
  try {
    renderBag(await api(`/carts/${state.cartId}`));
  } catch (error) {
    if (error.status === 404) {
      forgetCart();
      renderBag({ items: [], subtotal_cents: 0 });
    } else {
      toast(error.message);
    }
  }
}

async function changeQuantity(item, quantity) {
  try {
    if (quantity < 1) {
      await api(`/carts/${state.cartId}/items/${item.id}`, { method: "DELETE" });
    } else {
      await api(`/carts/${state.cartId}/items/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({ quantity }),
      });
    }
  } catch (error) {
    toast(error.message);
  }
  await refreshBag();
}

function renderBag(cart) {
  const count = cart.items.reduce((sum, item) => sum + item.quantity, 0);
  $("bag-count").textContent = count;
  $("bag-subtotal").textContent = money(cart.subtotal_cents);

  const remaining = 10001 - cart.subtotal_cents;
  $("bag-shipping-note").textContent = cart.items.length === 0
    ? ""
    : remaining > 0
      ? `Add ${money(remaining)} more for free shipping (orders over $100).`
      : "This order qualifies for free shipping.";

  $("bag-items").replaceChildren(
    ...(cart.items.length
      ? cart.items.map((item) =>
          el("div", { class: "bag-item" }, [
            el("div", {}, [
              el("div", { text: item.product_name }),
              el("div", { class: "meta", text: `${item.color} · ${item.size}` }),
              item.has_enough_stock
                ? null
                : el("div", { class: "meta", text: "Not enough stock" }),
            ]),
            el("div", { text: money(item.line_total_cents) }),
            el("div", { class: "qty" }, [
              el("button", { text: "−", "aria-label": "Decrease",
                             onclick: () => changeQuantity(item, item.quantity - 1) }),
              el("span", { text: String(item.quantity) }),
              el("button", { text: "+", "aria-label": "Increase",
                             onclick: () => changeQuantity(item, item.quantity + 1) }),
            ]),
            el("button", { class: "remove", text: "Remove",
                           onclick: () => changeQuantity(item, 0) }),
          ])
        )
      : [el("p", { class: "meta", text: "Your bag is empty." })])
  );
}

function openBag(open) {
  $("bag").hidden = !open;
  $("overlay").hidden = !open;
  if (open) refreshBag();
}

// ---------- Wiring ----------

let searchTimer;
$("search").addEventListener("input", (event) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.query = event.target.value.trim();
    renderProducts().catch((error) => toast(error.message));
  }, 250);
});
$("bag-button").addEventListener("click", () => openBag(true));
$("bag-close").addEventListener("click", () => openBag(false));
$("overlay").addEventListener("click", () => openBag(false));
$("menu-button").addEventListener("click", () =>
  $("categories").classList.toggle("open")
);

loadCatalog().catch(() =>
  toast("Could not load products. Is the API running and the catalog seeded?")
);
refreshBag();
