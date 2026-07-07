import { useState, useMemo } from "react";
import Navbar from "../components/Navbar";
import ListingCard from "../components/ListingCard";
import { useCart } from "../lib/CartContext";
import "./Marketplace.css";

/* ------------------------------------------------------------------ */
/*  Static data – replace with API call in the future                  */
/* ------------------------------------------------------------------ */
const STATIC_LISTINGS = [
  {
    id: 1,
    emoji: "🍅",
    name: "Fresh Organic Tomatoes",
    category: "Vegetables",
    quantity: "500 kg",
    price: "₹28 / kg",
    priceValue: 28,
    district: "Madurai",
    seller: "Rajan Farms",
    badge: "Organic",
    badgeColor: "#e8f5e9",
  },
  {
    id: 2,
    emoji: "🌾",
    name: "Basmati Rice (Grade A)",
    category: "Grains",
    quantity: "2 tonnes",
    price: "₹54 / kg",
    priceValue: 54,
    district: "Thanjavur",
    seller: "Kumaran Paddy",
    badge: "Premium",
    badgeColor: "#fff8e1",
  },
  {
    id: 3,
    emoji: "🧅",
    name: "Red Onions",
    category: "Vegetables",
    quantity: "800 kg",
    price: "₹22 / kg",
    priceValue: 22,
    district: "Salem",
    seller: "Vel Agro",
    badge: null,
    badgeColor: null,
  },
  {
    id: 4,
    emoji: "🥭",
    name: "Alphonso Mangoes",
    category: "Fruits",
    quantity: "200 kg",
    price: "₹120 / kg",
    priceValue: 120,
    district: "Krishnagiri",
    seller: "Mango Grove Co.",
    badge: "Seasonal",
    badgeColor: "#fff3e0",
  },
  {
    id: 5,
    emoji: "🌶️",
    name: "Guntur Red Chilli",
    category: "Spices",
    quantity: "350 kg",
    price: "₹85 / kg",
    priceValue: 85,
    district: "Coimbatore",
    seller: "Spice Route",
    badge: "Hot",
    badgeColor: "#fce4ec",
  },
  {
    id: 6,
    emoji: "🥬",
    name: "Fresh Spinach Bundles",
    category: "Vegetables",
    quantity: "150 kg",
    price: "₹30 / kg",
    priceValue: 30,
    district: "Tiruchirappalli",
    seller: "Green Leaf Farm",
    badge: "Fresh",
    badgeColor: "#e8f5e9",
  },
];

const CATEGORIES = [
  "All Categories",
  "Vegetables",
  "Fruits",
  "Grains",
  "Spices",
  "Dairy",
  "Equipment",
];

const DISTRICTS = [
  "All Districts",
  "Chennai",
  "Coimbatore",
  "Krishnagiri",
  "Madurai",
  "Salem",
  "Thanjavur",
  "Tiruchirappalli",
];

const PRICE_RANGES = [
  { label: "Any Price", min: 0, max: Infinity },
  { label: "Under ₹30/kg", min: 0, max: 30 },
  { label: "₹30 – ₹60/kg", min: 30, max: 60 },
  { label: "₹60 – ₹100/kg", min: 60, max: 100 },
  { label: "Above ₹100/kg", min: 100, max: Infinity },
];

/* ------------------------------------------------------------------ */

export default function Marketplace() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All Categories");
  const [district, setDistrict] = useState("All Districts");
  const [priceIdx, setPriceIdx] = useState(0);
  const { addToCart } = useCart();

  // Future: replace STATIC_LISTINGS with data from API / context
  const listings = STATIC_LISTINGS;

  const filtered = useMemo(() => {
    const range = PRICE_RANGES[priceIdx];
    return listings.filter((l) => {
      const matchSearch =
        l.name.toLowerCase().includes(search.toLowerCase()) ||
        l.seller.toLowerCase().includes(search.toLowerCase());
      const matchCategory =
        category === "All Categories" || l.category === category;
      const matchDistrict =
        district === "All Districts" || l.district === district;
      const matchPrice =
        l.priceValue >= range.min && l.priceValue <= range.max;
      return matchSearch && matchCategory && matchDistrict && matchPrice;
    });
  }, [listings, search, category, district, priceIdx]);

  function handleViewDetails(listing) {
    // Placeholder – wire up to a detail modal / route in the future
    alert(`Viewing details for: ${listing.name}\nSeller: ${listing.seller}`);
  }

  function handleAddToCart(listing) {
    addToCart(listing);
    alert(`Added ${listing.name} to cart!`);
  }

  function clearFilters() {
    setSearch("");
    setCategory("All Categories");
    setDistrict("All Districts");
    setPriceIdx(0);
  }

  const hasActiveFilter =
    search || category !== "All Categories" || district !== "All Districts" || priceIdx !== 0;

  return (
    <div className="mp-page">
      <Navbar />

      {/* ——— Hero banner ——— */}
      <header className="mp-hero">
        <div className="mp-hero-inner">
          <p className="mp-eyebrow">AGRICULTURE MARKETPLACE</p>
          <h1 className="mp-title">
            Fresh from the <span>farm</span> to you
          </h1>
          <p className="mp-subtitle">
            Browse crops, produce, and farm products listed directly by Tamil Nadu farmers.
          </p>
        </div>
        <div className="mp-hero-decoration" aria-hidden="true">🌿</div>
      </header>

      <main className="mp-main">
        {/* ——— Filter bar ——— */}
        <section className="mp-filters" aria-label="Listing filters">
          {/* Search */}
          <div className="mp-search-wrap">
            <span className="mp-search-icon" aria-hidden="true">🔍</span>
            <input
              id="mp-search"
              type="search"
              className="mp-search"
              placeholder="Search products or sellers…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search products or sellers"
            />
          </div>

          {/* Category dropdown */}
          <div className="mp-select-wrap">
            <label htmlFor="mp-category" className="mp-select-label">
              Category
            </label>
            <select
              id="mp-category"
              className="mp-select"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* District dropdown */}
          <div className="mp-select-wrap">
            <label htmlFor="mp-district" className="mp-select-label">
              District
            </label>
            <select
              id="mp-district"
              className="mp-select"
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
            >
              {DISTRICTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Price filter */}
          <div className="mp-select-wrap">
            <label htmlFor="mp-price" className="mp-select-label">
              Price range
            </label>
            <select
              id="mp-price"
              className="mp-select"
              value={priceIdx}
              onChange={(e) => setPriceIdx(Number(e.target.value))}
            >
              {PRICE_RANGES.map((r, i) => (
                <option key={r.label} value={i}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          {hasActiveFilter && (
            <button className="mp-clear-btn" onClick={clearFilters} aria-label="Clear all filters">
              ✕ Clear
            </button>
          )}
        </section>

        {/* ——— Results summary ——— */}
        <div className="mp-results-bar">
          <p className="mp-results-count">
            Showing <strong>{filtered.length}</strong> listing{filtered.length !== 1 ? "s" : ""}
          </p>
          {hasActiveFilter && (
            <span className="mp-filter-tag">Filtered</span>
          )}
        </div>

        {/* ——— Listings grid ——— */}
        {filtered.length > 0 ? (
          <div className="mp-grid">
            {filtered.map((listing) => (
              <ListingCard
                key={listing.id}
                {...listing}
                onView={() => handleViewDetails(listing)}
                onAddToCart={() => handleAddToCart(listing)}
              />
            ))}
          </div>
        ) : (
          /* ——— Empty state ——— */
          <div className="mp-empty" role="status" aria-live="polite">
            <div className="mp-empty-icon" aria-hidden="true">🌱</div>
            <h2 className="mp-empty-title">No listings found</h2>
            <p className="mp-empty-desc">
              We couldn&apos;t find any products matching your filters.
              <br />
              Try adjusting your search or clearing the filters.
            </p>
            <button className="mp-empty-btn" onClick={clearFilters}>
              Clear Filters
            </button>
          </div>
        )}

        {/* ——— CTA section ——— */}
        <section className="mp-cta">
          <div>
            <p className="mp-eyebrow" style={{ color: "#9fd7a6" }}>LIST YOUR PRODUCE</p>
            <h2>Got crops to sell?</h2>
            <p>
              Join hundreds of farmers already listing on AgriConnect AI. It&apos;s free and
              takes less than 5 minutes.
            </p>
          </div>
          <button className="mp-cta-btn">List a Product</button>
        </section>
      </main>
    </div>
  );
}

