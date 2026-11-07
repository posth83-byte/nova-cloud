app.js

document.addEventListener('DOMContentLoaded', () => {
    // --- PRODUKTKATALOG (EXAKT ENLIGT WEBMASTERS UNDERLAG) ---
    const products = [
        {
            id: 1,
            name: "Horizon Smartklocka",
            price: 1499,
            category: "Smart Living & Hem",
            image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80",
            shortDesc: "Elegant och minimalistisk smartklocka med hälso- och sömnmätning.",
            description: "Horizon Smartklocka förenar tidlös estetik med avancerad teknik. Med upp till 7 dagars batteritid, pulsmätning, sömnanalys och notiser direkt på handleden är den din perfekta följeslagare i vardagen. Boett i rostfritt stål och utbytbart armband i äkta läder."
        },
        {
            id: 2,
            name: "Aero Trådlösa Hörlurar",
            price: 1299,
            category: "Ljud & Underhållning",
            image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80",
            shortDesc: "Aktiv brusreducering och kristallklart ljud för den kräsne.",
            description: "Upplev totalt fokus med Aero trådlösa hörlurar. Utrustade med marknadsledande aktiv brusreducering (ANC) och ett balanserat ljudregister med djup bas och klara diskanter. Ergonomisk design som sitter bekvämt under långa lyssningsstunder."
        },
        {
            id: 3,
            name: "Urban Weekender Väska",
            price: 899,
            category: "Mode & Accessoarer",
            image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=800&q=80",
            shortDesc: "Slitstark och rymlig väska tillverkad i vattenavvisande kanvas.",
            description: "Urban Weekender är skapad för både weekendresan och den dagliga pendlingen. Tillverkad i kraftig, vattenavvisande kanvas med detaljer i vegetabiliskt garvat läder. Smarta innerfack håller ordning på din dator, laddare och personliga tillhörigheter."
        },
        {
            id: 4,
            name: "Aurora Designlampa",
            price: 649,
            category: "Belysning & Miljö",
            image: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80",
            shortDesc: "Dimbar bordslampa med varmt, stämningsfullt ljus och touch-kontroll.",
            description: "Aurora Designlampa sprider ett behagligt och varmt sken i rummet. Med steglös touch-dimring och sladdlös konstruktion kan du enkelt placera den där ljuset behövs som mest. Stilren skandinavisk formgivning i mattlackerad metall."
        }
    ];

    // --- KUNDVAGN & APPLIKATIONSSTATE ---
    let cart = [];

    // --- DOM-ELEMENT ---
    const productGrid = document.getElementById('product-grid');
    const cartBtn = document.getElementById('cart-btn');
    const cartCount = document.getElementById('cart-count');
    const cartModal = document.getElementById('cart-modal');
    const closeCartBtn = document.getElementById('close-cart');
    const cartItemsContainer = document.getElementById('cart-items');
    const cartSubtotalEl = document.getElementById('cart-subtotal');
    const cartShippingEl = document.getElementById('cart-shipping');
    const cartTotalEl = document.getElementById('cart-total');
    const checkoutBtn = document.getElementById('checkout-btn');

    // Produktmodal-element
    const productModal = document.getElementById('product-modal');
    const closeProductModalBtn = document.getElementById('close-product-modal');
    const modalProductImage = document.getElementById('modal-product-image');
    const modalProductCategory = document.getElementById('modal-product-category');
    const modalProductName = document.getElementById('modal-product-name');
    const modalProductPrice = document.getElementById('modal-product-price');
    const modalProductDesc = document.getElementById('modal-product-desc');
    const modalAddToCartBtn = document.getElementById('modal-add-to-cart');

    let currentModalProductId = null;

    // --- RENDERA PRODUKTKATALOG ---
    function renderProducts() {
        if (!productGrid) return;
        productGrid.innerHTML = products.map(product => `
            <div class="group bg-white border border-zinc-200 rounded-2xl overflow-hidden flex flex-col justify-between hover:border-zinc-400 transition-all shadow-xs">
                <div class="aspect-[4/3] bg-zinc-100 overflow-hidden relative cursor-pointer product-click" data-id="${product.id}">
                    <img src="${product.image}" alt="${product.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500">
                    <span class="absolute top-3 left-3 bg-white/90 backdrop-blur-xs text-zinc-800 text-xs font-medium px-2.5 py-1 rounded-full">${product.category}</span>
                </div>
                <div class="p-6 flex flex-col flex-grow justify-between">
                    <div>
                        <h3 class="font-bold text-lg text-zinc-900 mb-1 cursor-pointer product-click hover:text-zinc-600 transition-colors" data-id="${product.id}">${product.name}</h3>
                        <p class="text-sm text-zinc-600 mb-4 line-clamp-2">${product.shortDesc}</p>
                    </div>
                    <div class="flex items-center justify-between pt-4 border-t border-zinc-100">
                        <span class="text-lg font-bold text-zinc-900">${product.price} SEK</span>
                        <button class="add-to-cart-btn bg-zinc-900 hover:bg-zinc-800 text-white text-sm font-medium px-4 py-2 rounded-full transition-all cursor-pointer" data-id="${product.id}">
                            Köp
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        // Koppla händelselyssnare till nyligen renderade element
        document.querySelectorAll('.product-click').forEach(el => {
            el.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                openProductModal(id);
            });
        });

        document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = parseInt(e.target.getAttribute('data-id'));
                addToCart(id);
            });
        });
    }

    // --- PRODUKTMODAL ---
    function openProductModal(id) {
        const product = products.find(p => p.id === id);
        if (!product) return;

        currentModalProductId = product.id;
        modalProductImage.src = product.image;
        modalProductImage.alt = product.name;
        modalProductCategory.textContent = product.category;
        modalProductName.textContent = product.name;
        modalProductPrice.textContent = `${product.price} SEK`;
        modalProductDesc.textContent = product.description;

        productModal.classList.remove('hidden');
        productModal.classList.add('flex');
    }

    function closeProductModal() {
        productModal.classList.remove('flex');
        productModal.classList.add('hidden');
        currentModalProductId = null;
    }

    if (closeProductModalBtn) {
        closeProductModalBtn.addEventListener('click', closeProductModal);
    }

    if (modalAddToCartBtn) {
        modalAddToCartBtn.addEventListener('click', () => {
            if (currentModalProductId !== null) {
                addToCart(currentModalProductId);
                closeProductModal();
            }
        });
    }

    // Stäng modal vid klick utanför
    window.addEventListener('click', (e) => {
        if (e.target === productModal) {
            closeProductModal();
        }
        if (e.target === cartModal) {
            toggleCart(false);
        }
    });

    // --- KUNDVAGN LOGIK ---
    function addToCart(id) {
        const product = products.find(p => p.id === id);
        if (!product) return;

        const existingItem = cart.find(item => item.id === id);
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            cart.push({ ...product, quantity: 1 });
        }

        updateCartUI();
        toggleCart(true);
    }

    function removeFromCart(id) {
        cart = cart.filter(item => item.id !== id);
        updateCartUI();
    }

    function updateQuantity(id, change) {
        const item = cart.find(item => item.id === id);
        if (item) {
            item.quantity += change;
            if (item.quantity <= 0) {
                removeFromCart(id);
            } else {
                updateCartUI();
            }
        }
    }

    function updateCartUI() {
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        cartCount.textContent = totalItems;

        if (cart.length === 0) {
            cartItemsContainer.innerHTML = `
                <div class="text-center py-12 text-zinc-500">
                    <p>Din kundvagn är tom.</p>
                </div>
            `;
            cartSubtotalEl.textContent = '0 SEK';
            cartShippingEl.textContent = '0 SEK';
            cartTotalEl.textContent = '0 SEK';
            checkoutBtn.disabled = true;
            checkoutBtn.classList.add('opacity-50', 'cursor-not-allowed');
            return;
        }

        checkoutBtn.disabled = false;
        checkoutBtn.classList.remove('opacity-50', 'cursor-not-allowed');

        cartItemsContainer.innerHTML = cart.map(item => `
            <div class="flex items-center justify-between py-4 border-b border-zinc-100">
                <div class="flex items-center space-x-4">
                    <img src="${item.image}" alt="${item.name}" class="w-16 h-16 object-cover rounded-xl border border-zinc-200">
                    <div>
                        <h4 class="font-bold text-zinc-900 text-sm">${item.name}</h4>
                        <p class="text-xs text-zinc-500">${item.price} SEK / st</p>
                        <div class="flex items-center space-x-2 mt-2">
                            <button class="decrease-qty w-6 h-6 rounded-full bg-zinc-100 hover:bg-zinc-200 text-zinc-800 flex items-center justify-center text-xs font-bold transition-all" data-id="${item.id}">-</button>
                            <span class="text-sm font-medium w-6 text-center">${item.quantity}</span>
                            <button class="increase-qty w-6 h-6 rounded-full bg-zinc-100 hover:bg-zinc-200 text-zinc-800 flex items-center justify-center text-xs font-bold transition-all" data-id="${item.id}">+</button>
                        </div>
                    </div>
                </div>
                <div class="text-right">
                    <span class="font-bold text-zinc-900 text-sm block mb-2">${item.price * item.quantity} SEK</span>
                    <button class="remove-item text-xs text-red-500 hover:text-red-700 transition-colors" data-id="${item.id}">Ta bort</button>
                </div>
            </div>
        `).join('');

        // Bind händelser till kundvagnens knappar
        cartItemsContainer.querySelectorAll('.increase-qty').forEach(btn => {
            btn.addEventListener('click', (e) => updateQuantity(parseInt(e.target.getAttribute('data-id')), 1));
        });

        cartItemsContainer.querySelectorAll('.decrease-qty').forEach(btn => {
            btn.addEventListener('click', (e) => updateQuantity(parseInt(e.target.getAttribute('data-id')), -1));
        });

        cartItemsContainer.querySelectorAll('.remove-item').forEach(btn => {
            btn.addEventListener('click', (e) => removeFromCart(parseInt(e.target.getAttribute('data-id'))));
        });

        // Beräkningar
        const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const shipping = subtotal >= 500 || subtotal === 0 ? 0 : 49;
        const total = subtotal + shipping;

        cartSubtotalEl.textContent = `${subtotal} SEK`;
        cartShippingEl.textContent = shipping === 0 ? 'Fri frakt' : `${shipping} SEK`;
        cartTotalEl.textContent = `${total} SEK`;
    }

    function toggleCart(show) {
        if (show) {
            cartModal.classList.remove('hidden');
            cartModal.classList.add('flex');
        } else {
            cartModal.classList.remove('flex');
            cartModal.classList.add('hidden');
        }
    }

    if (cartBtn) {
        cartBtn.addEventListener('click', () => toggleCart(true));
    }

    if (closeCartBtn) {
        closeCartBtn.addEventListener('click', () => toggleCart(false));
    }

    // --- KASSA / CHECKOUT (TESTLÄGE) ---
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', () => {
            if (cart.length === 0) return;
            alert('TESTKASSA: Tack för din simulerade beställning hos NEXORA!\n\nEftersom betalningsintegration är i testläge har ingen faktisk transaktion genomförts. En orderbekräftelse har simulerats internt.');
            cart = [];
            updateCartUI();
            toggleCart(false);
        });
    }

    // Initiera applikationen
    renderProducts();
    updateCartUI();
});