document.addEventListener("DOMContentLoaded", () => {
    const products = [
        {
            id: 1,
            title: "Nordic Lampa",
            category: "belysning",
            price: 1299,
            imageText: "Minimalistisk taklampa i mässing och frostat glas.",
            description: "En elegant ljuskälla som sprider ett varmt och behagligt sken över matbordet eller i vardagsrummet."
        },
        {
            id: 2,
            title: "Ullpläd Stockholm",
            category: "textil",
            price: 899,
            imageText: "Mjuk pläd av 100% gotländsk ull.",
            description: "Handvävd lyx för kyliga kvällar. Tidlös skandinavisk design med diskreta fransar."
        },
        {
            id: 3,
            title: "Keramikmugg Kust",
            category: "kok",
            price: 249,
            imageText: "Handgjord stengodsmugg med reaktiv glasyr.",
            description: "Varje mugg är unik. Tål maskindisk och mikro, perfekt för morgonkaffet."
        },
        {
            id: 4,
            title: "Ekologisk Doftljus Vinter",
            category: "hem",
            price: 349,
            imageText: "Sojavax med doft av granbarr och bärnsten.",
            description: "Skapar en harmonisk och rogivande atmosfär i hemmet med naturliga eteriska oljor."
        },
        {
            id: 5,
            title: "Sidobord Minimal",
            category: "mobler",
            price: 1899,
            imageText: "Pulverlackad stålkonstruktion med matt finish.",
            description: "Ett nätt och stabilt bord som passar lika bra som sängbord som vid soffan."
        },
        {
            id: 6,
            title: "Linneservett Natur (4-pack)",
            category: "textil",
            price: 450,
            imageText: "Förtvättat hellinne med mjuk känsla.",
            description: "Ger dukningen en avslappnad men sofistikerad touch. Blir bara vackrare ju mer de används."
        }
    ];

    let cart = JSON.parse(localStorage.getItem("nexora_cart")) || [];
    let activeFilter = "all";

    const productGrid = document.getElementById("productGrid");
    const filterButtons = document.querySelectorAll(".filter-btn");
    const cartBtn = document.getElementById("cartBtn");
    const cartCount = document.getElementById("cartCount");
    const cartModal = document.getElementById("cartModal");
    const closeCart = document.getElementById("closeCart");
    const cartItems = document.getElementById("cartItems");
    const cartTotal = document.getElementById("cartTotal");
    const checkoutBtn = document.getElementById("checkoutBtn");
    const checkoutModal = document.getElementById("checkoutModal");
    const closeCheckout = document.getElementById("closeCheckout");
    const checkoutForm = document.getElementById("checkoutForm");
    const confirmationModal = document.getElementById("confirmationModal");
    const closeConfirmation = document.getElementById("closeConfirmation");
    const orderNumberSpan = document.getElementById("orderNumber");
    const yearSpan = document.getElementById("currentYear");

    if (yearSpan) {
        yearSpan.textContent = new Date().getFullYear();
    }

    function renderProducts() {
        if (!productGrid) return;
        productGrid.innerHTML = "";

        const filtered = activeFilter === "all"
            ? products
            : products.filter(p => p.category === activeFilter);

        filtered.forEach(product => {
            const card = document.createElement("div");
            card.className = "product-card";
            card.innerHTML = `
                <div class="product-img">
                    <span>${product.imageText}</span>
                </div>
                <div class="product-info">
                    <span class="product-category">${product.category}</span>
                    <h3 class="product-title">${product.title}</h3>
                    <p class="product-desc">${product.description}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: auto;">
                        <span style="font-weight: 600; font-size: 1.1rem;">${product.price} SEK</span>
                        <button class="btn-primary" style="width: auto; padding: 0.5rem 1rem;" data-id="${product.id}">Köp</button>
                    </div>
                </div>
            `;
            productGrid.appendChild(card);
        });

        document.querySelectorAll(".product-card button").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const id = parseInt(e.target.getAttribute("data-id"));
                addToCart(id);
            });
        });
    }

    function addToCart(productId) {
        const product = products.find(p => p.id === productId);
        if (!product) return;

        const existing = cart.find(item => item.id === productId);
        if (existing) {
            existing.quantity += 1;
        } else {
            cart.push({ ...product, quantity: 1 });
        }

        saveCart();
        updateCartUI();
        openModal(cartModal);
    }

    function saveCart() {
        localStorage.setItem("nexora_cart", JSON.stringify(cart));
    }

    function updateCartUI() {
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        if (cartCount) cartCount.textContent = totalItems;

        if (!cartItems) return;
        cartItems.innerHTML = "";

        if (cart.length === 0) {
            cartItems.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 2rem 0;">Din kundvagn är tom.</p>`;
            if (cartTotal) cartTotal.textContent = "0 SEK";
            return;
        }

        let sumPrice = 0;

        cart.forEach(item => {
            sumPrice += item.price * item.quantity;
            const row = document.createElement("div");
            row.style.display = "flex";
            row.style.justifyContent = "space-between";
            row.style.alignItems: "center";
            row.style.padding = "1rem 0";
            row.style.borderBottom = "1px solid var(--border-color)";

            row.innerHTML = `
                <div>
                    <h4 style="font-size: 0.95rem; font-weight: 500;">${item.title}</h4>
                    <span style="font-size: 0.85rem; color: var(--text-muted);">${item.price} SEK st</span>
                </div>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="display: flex; align-items: center; border: 1px solid var(--border-color); border-radius: var(--radius);">
                        <button class="qty-btn" data-id="${item.id}" data-action="decrease" style="background: none; border: none; padding: 0.25rem 0.5rem; cursor: pointer;">-</button>
                        <span style="padding: 0 0.5rem; font-size: 0.9rem;">${item.quantity}</span>
                        <button class="qty-btn" data-id="${item.id}" data-action="increase" style="background: none; border: none; padding: 0.25rem 0.5rem; cursor: pointer;">+</button>
                    </div>
                    <button class="remove-btn" data-id="${item.id}" style="background: none; border: none; color: #999; cursor: pointer; font-size: 0.9rem;">Ta bort</button>
                </div>
            `;
            cartItems.appendChild(row);
        });

        if (cartTotal) cartTotal.textContent = `${sumPrice} SEK`;

        document.querySelectorAll(".qty-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const id = parseInt(e.target.getAttribute("data-id"));
                const action = e.target.getAttribute("data-action");
                adjustQuantity(id, action);
            });
        });

        document.querySelectorAll(".remove-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const id = parseInt(e.target.getAttribute("data-id"));
                removeFromCart(id);
            });
        });
    }

    function adjustQuantity(productId, action) {
        const item = cart.find(i => i.id === productId);
        if (!item) return;

        if (action === "increase") {
            item.quantity += 1;
        } else if (action === "decrease") {
            item.quantity -= 1;
            if (item.quantity <= 0) {
                cart = cart.filter(i => i.id !== productId);
            }
        }

        saveCart();
        updateCartUI();
    }

    function removeFromCart(productId) {
        cart = cart.filter(i => i.id !== productId);
        saveCart();
        updateCartUI();
    }

    function openModal(modal) {
        if (modal) modal.style.display = "flex";
    }

    function closeModal(modal) {
        if (modal) modal.style.display = "none";
    }

    filterButtons.forEach(btn => {
        btn.addEventListener("click", (e) => {
            filterButtons.forEach(b => b.classList.remove("active"));
            e.target.classList.add("active");
            activeFilter = e.target.getAttribute("data-filter");
            renderProducts();
        });
    });

    if (cartBtn) {
        cartBtn.addEventListener("click", () => {
            updateCartUI();
            openModal(cartModal);
        });
    }

    if (closeCart) {
        closeCart.addEventListener("click", () => closeModal(cartModal));
    }

    if (checkoutBtn) {
        checkoutBtn.addEventListener("click", () => {
            if (cart.length === 0) return;
            closeModal(cartModal);
            openModal(checkoutModal);
        });
    }

    if (closeCheckout) {
        closeCheckout.addEventListener("click", () => closeModal(checkoutModal));
    }

    if (closeConfirmation) {
        closeConfirmation.addEventListener("click", () => closeModal(confirmationModal));
    }

    window.addEventListener("click", (e) => {
        if (e.target === cartModal) closeModal(cartModal);
        if (e.target === checkoutModal) closeModal(checkoutModal);
        if (e.target === confirmationModal) closeModal(confirmationModal);
    });

    if (checkoutForm) {
        checkoutForm.addEventListener("submit", (e) => {
            e.preventDefault();

            const name = document.getElementById("name").value.trim();
            const email = document.getElementById("email").value.trim();
            const address = document.getElementById("address").value.trim();
            const city = document.getElementById("city").value.trim();
            const zip = document.getElementById("zip").value.trim();

            if (!name || !email || !address || !city || !zip) {
                alert("Vänligen fyll i alla fält korrekt.");
                return;
            }

            const randomOrderNum = "NX-" + Math.floor(100000 + Math.random() * 900000);
            if (orderNumberSpan) orderNumberSpan.textContent = randomOrderNum;

            cart = [];
            saveCart();
            updateCartUI();

            closeModal(checkoutModal);
            checkoutForm.reset();
            openModal(confirmationModal);
        });
    }

    renderProducts();
    updateCartUI();
});