import "./App.css";

function App() {
  return (
    <div className="app">
      <nav className="navbar">
        <div className="logo">
          <span className="logo-mark">🌾</span>
          <span>AgriConnect AI</span>
        </div>

        <div className="nav-links">
          <a href="#marketplace">Marketplace</a>
          <a href="#rentals">Rentals</a>
          <a href="#features">How it works</a>
        </div>

        <div className="nav-actions">
          <button className="login-btn">Log in</button>
          <button className="primary-btn">Join as Farmer</button>
        </div>
      </nav>

      <main>
        <section className="hero">
          <div className="hero-content">
            <p className="eyebrow">SMART AGRICULTURE MARKETPLACE</p>

            <h1>
              Sell crops. Rent equipment.
              <span> Grow smarter.</span>
            </h1>

            <p className="hero-description">
              AgriConnect AI connects farmers, buyers, and equipment owners
              through one trusted digital marketplace.
            </p>

            <div className="hero-buttons">
              <button className="primary-btn large-btn">
                Explore Marketplace
              </button>
              <button className="secondary-btn large-btn">
                List Your Product
              </button>
            </div>

            <div className="hero-stats">
              <div>
                <strong>500+</strong>
                <span>Farmer listings</span>
              </div>
              <div>
                <strong>120+</strong>
                <span>Equipment rentals</span>
              </div>
              <div>
                <strong>24/7</strong>
                <span>AI assistance</span>
              </div>
            </div>
          </div>

          <div className="hero-card">
            <p className="card-label">FEATURED LISTING</p>
            <div className="crop-image">🍅</div>
            <h3>Fresh Organic Tomatoes</h3>
            <p>Madurai, Tamil Nadu</p>

            <div className="listing-details">
              <span>500 kg available</span>
              <strong>₹28 / kg</strong>
            </div>

            <button className="view-btn">View Listing →</button>
          </div>
        </section>

        <section className="categories" id="marketplace">
          <div className="section-heading">
            <p className="eyebrow">EXPLORE THE PLATFORM</p>
            <h2>Everything farmers need in one place</h2>
            <p>
              Buy, sell, rent, and discover agricultural opportunities near
              you.
            </p>
          </div>

          <div className="feature-grid" id="features">
            <article className="feature-card">
              <div className="feature-icon">🧺</div>
              <h3>Sell Farm Products</h3>
              <p>
                List vegetables, fruits, grains, seeds, and farm-made products
                directly for buyers.
              </p>
              <a href="#sell">Start selling →</a>
            </article>

            <article className="feature-card" id="rentals">
              <div className="feature-icon">🚜</div>
              <h3>Rent Equipment</h3>
              <p>
                Find tractors, harvesters, sprayers, and farm equipment near
                your district.
              </p>
              <a href="#rent">Explore rentals →</a>
            </article>

            <article className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3>Ask AgriConnect AI</h3>
              <p>
                Get help finding listings, understanding rentals, and using
                the platform.
              </p>
              <a href="#assistant">Ask the assistant →</a>
            </article>
          </div>
        </section>

        <section className="cta-section">
          <div>
            <p className="eyebrow">START TODAY</p>
            <h2>Ready to grow your agricultural business?</h2>
            <p>
              Join AgriConnect AI to reach buyers, discover equipment, and
              simplify farm commerce.
            </p>
          </div>

          <button className="primary-btn large-btn">Create Free Account</button>
        </section>
      </main>
    </div>
  );
}

export default App;