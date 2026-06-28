import "./ListingCard.css";

/**
 * ListingCard  – reusable product card for the marketplace
 *
 * Props:
 *  emoji       – string emoji used as the product image placeholder
 *  name        – product name
 *  category    – category label (e.g. "Vegetables")
 *  quantity    – e.g. "500 kg"
 *  price       – e.g. "₹28 / kg"
 *  district    – location string
 *  seller      – seller name
 *  badge       – optional badge text (e.g. "Organic", "Fresh")
 *  badgeColor  – optional CSS color for the badge background
 *  onView      – callback for the "View Details" button
 */
export default function ListingCard({
  emoji = "🌾",
  name = "Farm Product",
  category = "Uncategorized",
  quantity = "—",
  price = "—",
  district = "—",
  seller = "Unknown Seller",
  badge = null,
  badgeColor = "#e8f5e9",
  onView,
  onAddToCart,
}) {
  return (
    <article className="listing-card">
      {/* image placeholder */}
      <div className="lc-image-wrap">
        <span className="lc-emoji" role="img" aria-label={name}>
          {emoji}
        </span>
        {badge && (
          <span className="lc-badge" style={{ background: badgeColor }}>
            {badge}
          </span>
        )}
      </div>

      <div className="lc-body">
        <p className="lc-category">{category}</p>
        <h3 className="lc-name">{name}</h3>

        <div className="lc-meta">
          <span className="lc-meta-item">
            <span className="lc-icon">📦</span> {quantity}
          </span>
          <span className="lc-meta-item lc-price">
            <span className="lc-icon">💰</span> {price}
          </span>
        </div>

        <div className="lc-footer">
          <div className="lc-location">
            <span className="lc-icon">📍</span>
            <span>{district}</span>
          </div>
          <div className="lc-seller">
            <span className="lc-avatar">{seller[0]}</span>
            <span>{seller}</span>
          </div>
        </div>

        <div className="lc-buttons-row" style={{ display: "flex", gap: "8px", marginTop: "auto" }}>
          <button
            type="button"
            className="lc-view-btn"
            onClick={onView}
            aria-label={`View details for ${name}`}
            style={{ flex: 1 }}
          >
            Details
          </button>
          
          <button
            type="button"
            className="lc-add-cart-btn"
            onClick={onAddToCart}
            aria-label={`Add ${name} to cart`}
            style={{
              flex: 1.2,
              padding: "12px",
              borderRadius: "10px",
              background: "#2f7d32",
              border: "none",
              color: "#fff",
              fontWeight: "800",
              fontSize: "13.5px",
              cursor: "pointer",
              transition: "background 0.18s"
            }}
          >
            🛒 Add to Cart
          </button>
        </div>
      </div>
    </article>
  );
}

