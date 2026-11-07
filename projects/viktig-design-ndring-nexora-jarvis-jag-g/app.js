const products = [
    {
        id: 1,
        name: "Nexora Horizon Pro Trådlösa Hörlurar",
        category: "Elektronik",
        price: 1899,
        image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=1000&auto=format&fit=crop",
        description: "Upplev kristallklart ljud med aktiv brusreducering och en batteritid på upp till 30 timmar. Ergonomisk design för maximal komfort hela dagen.",
        specs: ["Aktiv brusreducering (ANC)", "30 timmars batteritid", "Bluetooth 5.3", "Snabbladdning (15 min = 3 timmar)"]
    },
    {
        id: 2,
        name: "Minimalistisk Titan-Klocka",
        category: "Accessoarer",
        price: 2499,
        image: "https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=1000&auto=format&fit=crop",
        description: "En elegant klocka tillverkad i lätt och tålig titan med safirglas och ett slitstarkt armband i äkta läder. Vattentålig upp till 5 ATM.",
        specs: ["Boett i titan", "Safirglas", "Äkta läderarmband", "Vattentålig 5 ATM"]
    },
    {
        id: 3,
        name: "Nordic Ceramic Bordslampa",
        category: "Hem",
        price: 899,
        image: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?q=80&w=1000&auto=format&fit=crop",
        description: "Skapa en varm och inbjudande atmosfär i hemmet med denna handgjorda keramiska bordslampa i skandinavisk design.",
        specs: ["Handgjord keramik", "Dimmerfunktion", "E27 sockel", "Textilklädd sladd"]
    },
    {
        id: 4,
        name: "Apex Ergonomisk Ryggsäck",
        category: "Accessoarer",
        price: 1299,
        image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?q=80&w=1000&auto=format&fit=crop",
        description: "Den perfekta vardagsryggsäcken med dedikerat fack för 15-tums laptop, vattenavvisande material och smarta förvaringslösningar.",
        specs: ["15\" laptopfack", "Vattenavvisande tyg", "Ergonomiska axelremmar", "20 liters volym"]
    },
    {
        id: 5,
        name: "Aura Smart Luftfuktare",
        category: "Hem",
        price: 1199,
        image: "https://images.unsplash.com/photo-1585771724684-38269d6639fd?q=80&w=1000&auto=format&fit=crop",
        description: "Förbättrar inomhusklimatet tyst och effektivt. Styr enkelt via touchpanel eller mobilapp.",
        specs: ["Tyst drift (< 26dB)", "4 liters vattentank", "Automatisk fuktighetskontroll", "Aromaterapi-funktion"]
    },
    {
        id: 6,
        name: "Pulse Portable Bluetooth-högtalare",
        category: "Elektronik",
        price: 1499,
        image: "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?q=80&w=1000&auto=format&fit=crop",
        description: "Kraftfullt 360-graders ljud i ett kompakt och vattentåligt format (IPX7). Perfekt för både hemmet och stranden.",
        specs: ["360° ljudbild", "IPX7 Vattentålig", "20 timmars batteritid", "True Wireless Stereo-koppling"]
    }
];

let cart = JSON.parse(localStorage.getItem('nexora_cart')) || [];
let currentCategoryFilter = 'All';

const router = {
    navigate: function(view, param = null) {
        window.scrollTo(0, 0);
        const container = document.getElementById('app-container');
        if (!container) return;

        switch(view) {
            case 'home':
                container.innerHTML = renderHome();
                break;
            case 'catalog':
                container.innerHTML = renderCatalog();
                break;
            case 'product':
                container.innerHTML = renderProductDetail(param);
                break;
            case 'cart':
                container.innerHTML = renderCart();
                break;
            case 'checkout':
                container.innerHTML = renderCheckout();
                break;
            case 'order-success':
                container.innerHTML = renderOrderSuccess(param);
                break;
            case 'about':
                container.innerHTML = renderAbout();
                break;
            case 'contact':
                container.innerHTML = renderContact();
                break;
            case 'terms':
                container.innerHTML = renderTerms();
                break;
            case 'returns':
                container.innerHTML = renderReturns();
                break;
            case 'faq':
                container.innerHTML = renderFaq();
                break;
            default:
                container.innerHTML = renderHome();
        }
        updateCartBadge();
    }
};

function updateCartBadge() {
    const badge = document.getElementById('cart-badge');
    if (badge) {
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        badge.textContent = totalItems;
    }
    localStorage.setItem('nexora_cart', JSON.stringify(cart));
}

function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

function filterCategory(category) {
    currentCategoryFilter = category;
    const catalogContainer = document.getElementById('catalog-products');
    if (catalogContainer) {
        catalogContainer.innerHTML = renderProductList(category);
    }
    document.querySelectorAll('.category-btn').forEach(btn => {
        if (btn.dataset.category === category) {
            btn.classList.add('bg-blue-600', 'text-white');
            btn.classList.remove('bg-gray-100', 'text-gray-700');
        } else {
            btn.classList.remove('bg-blue-600', 'text-white');
            btn.classList.add('bg-gray-100', 'text-gray-700');
        }
    });
}

function addToCart(productId, quantity = 1) {
    const product = products.find(p => p.id === productId);
    if (!product) return;

    const existingItem = cart.find(item => item.id === productId);
    if (existingItem) {
        existingItem.quantity += quantity;
    } else {
        cart.push({ ...product, quantity });
    }
    updateCartBadge();
    showNotification(`Lagt till "${product.name}" i kundvagnen!`);
}

function updateQuantity(productId, delta) {
    const item = cart.find(i => i.id === productId);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
        cart = cart.filter(i => i.id !== productId);
    }
    router.navigate('cart');
}

function removeFromCart(productId) {
    cart = cart.filter(i => i.id !== productId);
    router.navigate('cart');
}

function showNotification(message) {
    const existing = document.getElementById('toast-notification');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'toast-notification';
    toast.className = 'fixed bottom-5 right-5 z-50 bg-gray-900 text-white px-6 py-3 rounded-lg shadow-lg text-sm font-medium transition transform duration-300 translate-y-0';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function handleCheckoutSubmit(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const orderDetails = {
        name: formData.get('name'),
        email: formData.get('email'),
        address: formData.get('address'),
        city: formData.get('city'),
        zip: formData.get('zip'),
        paymentMethod: formData.get('paymentMethod'),
        items: [...cart],
        total: cart.reduce((sum, item) => sum + (item.price * item.quantity), 0),
        orderNumber: 'NX-' + Math.floor(100000 + Math.random() * 900000),
        date: new Date().toLocaleDateString('sv-SE')
    };
    cart = [];
    updateCartBadge();
    router.navigate('order-success', orderDetails);
}

function renderHome() {
    const featured = products.slice(0, 4);
    return `
        <!-- Hero Section -->
        <section class="bg-gray-50 border-b border-gray-200 py-20 px-4 sm:px-6 lg:px-8">
            <div class="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
                <div class="space-y-6">
                    <span class="bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wider">Ny kollektion ute nu</span>
                    <h1 class="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-gray-900 leading-tight">
                        Discover More. <br><span class="text-blue-600">Live Better.</span>
                    </h1>
                    <p class="text-lg text-gray-600 leading-relaxed">
                        Utforska vårt handplockade sortiment av moderna kvalitetsprodukter skapade för att förenkla och förhöja din vardag.
                    </p>
                    <div class="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4 pt-2">
                        <button onclick="router.navigate('catalog')" class="bg-blue-600 hover:bg-blue-700 text-white font-medium px-8 py-3.5 rounded-lg shadow transition text-center">
                            Utforska produkter
                        </button>
                        <button onclick="router.navigate('about')" class="bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 font-medium px-8 py-3.5 rounded-lg transition text-center">
                            Om Nexora
                        </button>
                    </div>
                </div>
                <div class="relative">
                    <img src="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=1000&auto=format&fit=crop" alt="Nexora Produkter" class="rounded-2xl shadow-xl w-full h-[450px] object-cover">
                </div>
            </div>
        </section>

        <!-- USP Bar -->
        <section class="border-b border-gray-200 bg-white py-10">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-3 gap-8 text-center md:text-left">
                <div class="flex items-center space-x-4 justify-center md:justify-start">
                    <div class="bg-blue-50 p-3 rounded-lg text-blue-600">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>
                    </div>
                    <div>
                        <h3 class="font-semibold text-gray-900">Fri frakt</h3>
                        <p class="text-sm text-gray-500">På alla ordrar över 490 kr</p>
                    </div>
                </div>
                <div class="flex items-center space-x-4 justify-center md:justify-start">
                    <div class="bg-blue-50 p-3 rounded-lg text-blue-600">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                    </div>
                    <div>
                        <h3 class="font-semibold text-gray-900">30 dagars öppet köp</h3>
                        <p class="text-sm text-gray-500">Handla tryggt och säkert</p>
                    </div>
                </div>
                <div class="flex items-center space-x-4 justify-center md:justify-start">
                    <div class="bg-blue-50 p-3 rounded-lg text-blue-600">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                    </div>
                    <div>
                        <h3 class="font-semibold text-gray-900">Snabb leverans</h3>
                        <p class="text-sm text-gray-500">1-3 arbetsdagar</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Featured Products -->
        <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div class="flex justify-between items-end mb-10">
                <div>
                    <h2 class="text-2xl sm:text-3xl font-bold text-gray-900">Utvalda produkter</h2>
                    <p class="text-gray-500 mt-1">Våra mest populära val just nu</p>
                </div>
                <button onclick="router.navigate('catalog')" class="text-blue-600 hover:text-blue-800 font-medium text-sm flex items-center space-x-1">
                    <span>Visa alla</span>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                </button>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
                ${featured.map(p => `
                    <div class="group bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition flex flex-col justify-between">
                        <div>
                            <div class="bg-gray-100 aspect-square overflow-hidden cursor-pointer" onclick="router.navigate('product', ${p.id})">
                                <img src="${p.image}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                            </div>
                            <div class="p-5">
                                <span class="text-xs text-gray-400 font-medium uppercase tracking-wider">${p.category}</span>
                                <h3 onclick="router.navigate('product', ${p.id})" class="font-semibold text-gray-900 mt-1 cursor-pointer hover:text-blue-600 transition">${p.name}</h3>
                                <p class="text-lg font-bold text-gray-900 mt-2">${p.price} kr</p>
                            </div>
                        </div>
                        <div class="p-5 pt-0">
                            <button onclick="addToCart(${p.id})" class="w-full bg-gray-900 hover:bg-blue-600 text-white font-medium py-2.5 px-4 rounded-lg transition text-sm">
                                Lägg i kundvagn
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        </section>
    `;
}

function renderCatalog() {
    return `
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="mb-8">
                <h1 class="text-3xl font-bold text-gray-900">Produktkatalog</h1>
                <p class="text-gray-500 mt-1">Utforska vårt kompletta utbud av kvalitetsprodukter.</p>
            </div>

            <!-- Categories Filter Buttons -->
            <div class="flex flex-wrap gap-2 mb-10 pb-6 border-b border-gray-200">
                <button onclick="filterCategory('All')" data-category="All" class="category-btn ${currentCategoryFilter === 'All' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'} px-5 py-2 rounded-lg font-medium text-sm transition">Alla produkter</button>
                <button onclick="filterCategory('Elektronik')" data-category="Elektronik" class="category-btn ${currentCategoryFilter === 'Elektronik' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'} px-5 py-2 rounded-lg font-medium text-sm transition">Elektronik</button>
                <button onclick="filterCategory('Accessoarer')" data-category="Accessoarer" class="category-btn ${currentCategoryFilter === 'Accessoarer' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'} px-5 py-2 rounded-lg font-medium text-sm transition">Accessoarer</button>
                <button onclick="filterCategory('Hem')" data-category="Hem" class="category-btn ${currentCategoryFilter === 'Hem' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'} px-5 py-2 rounded-lg font-medium text-sm transition">Hem & Livsstil</button>
            </div>

            <!-- Product Grid -->
            <div id="catalog-products" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
                ${renderProductList(currentCategoryFilter)}
            </div>
        </div>
    `;
}

function renderProductList(category) {
    const filtered = category === 'All' ? products : products.filter(p => p.category === category);
    
    if (filtered.length === 0) {
        return `<div class="col-span-full py-12 text-center text-gray-500">Inga produkter hittades i denna kategori.</div>`;
    }

    return filtered.map(p => `
        <div class="group bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-lg transition flex flex-col justify-between">
            <div>
                <div class="bg-gray-100 aspect-square overflow-hidden cursor-pointer" onclick="router.navigate('product', ${p.id})">
                    <img src="${p.image}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                </div>
                <div class="p-6">
                    <span class="text-xs text-gray-400 font-medium uppercase tracking-wider">${p.category}</span>
                    <h3 onclick="router.navigate('product', ${p.id})" class="font-semibold text-gray-900 text-lg mt-1 cursor-pointer hover:text-blue-600 transition">${p.name}</h3>
                    <p class="text-gray-500 text-sm mt-2 line-clamp-2">${p.description}</p>
                    <p class="text-xl font-bold text-gray-900 mt-4">${p.price} kr</p>
                </div>
            </div>
            <div class="p-6 pt-0">
                <button onclick="addToCart(${p.id})" class="w-full bg-gray-900 hover:bg-blue-600 text-white font-medium py-3 px-4 rounded-lg transition text-sm">
                    Lägg i kundvagn
                </button>
            </div>
        </div>
    `).join('');
}

function renderProductDetail(productId) {
    const product = products.find(p => p.id === productId) || products[0];
    return `
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <nav class="text-sm text-gray-500 mb-8 flex items-center space-x-2">
                <a href="#" onclick="router.navigate('home')" class="hover:underline">Startsida</a>
                <span>/</span>
                <a href="#" onclick="router.navigate('catalog')" class="hover:underline">Produkter</a>
                <span>/</span>
                <span class="text-gray-900 font-medium">${product.name}</span>
            </nav>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
                <!-- Large Product Image -->
                <div class="bg-gray-100 rounded-2xl overflow-hidden shadow-md aspect-square">
                    <img src="${product.image}" alt="${product.name}" class="w-full h-full object-cover">
                </div>

                <!-- Product Info -->
                <div class="space-y-6">
                    <div>
                        <span class="bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wider">${product.category}</span>
                        <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mt-3">${product.name}</h1>
                        <p class="text-2xl font-bold text-gray-900 mt-4">${product.price} kr</p>
                    </div>

                    <p class="text-gray-600 leading-relaxed text-base">${product.description}</p>

                    ${product.specs ? `
                        <div class="border-t border-b border-gray-200 py-6 space-y-3">
                            <h3 class="font-semibold text-gray-900">Specifikationer:</h3>
                            <ul class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-600">
                                ${product.specs.map(spec => `<li class="flex items-center space-x-2"><span class="w-1.5 h-1.5 bg-blue-600 rounded-full"></span><span>${spec}</span></li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}

                    <div class="flex items-center space-x-4 pt-4">
                        <button onclick="addToCart(${product.id})" class="flex-grow bg-blue-600 hover:bg-blue-700 text-white font-medium py-4 px-8 rounded-xl shadow transition text-center text-base">
                            Lägg i kundvagn
                        </button>
                    </div>

                    <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 text-sm text-gray-600 space-y-2">
                        <div class="flex items-center space-x-2">
                            <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                            <span>I lager - Skickas inom 24 timmar</span>
                        </div>
                        <div class="flex items-center space-x-2">
                            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                            <span>30 dagars öppet köp och fri retur</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderCart() {
    if (cart.length === 0) {
        return `
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
                <div class="max-w-md mx-auto space-y-6">
                    <div class="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto text-gray-400">
                        <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path></svg>
                    </div>
                    <h1 class="text-3xl font-bold text-gray-900">Din kundvagn är tom</h1>
                    <p class="text-gray-500">Du har inte lagt till några produkter i din kundvagn ännu.</p>
                    <button onclick="router.navigate('catalog')" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3.5 px-6 rounded-lg shadow transition">
                        Till produktkatalogen
                    </button>
                </div>
            </div>
        `;
    }

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const shipping = subtotal >= 490 ? 0 : 49;
    const total = subtotal + shipping;

    return `
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <h1 class="text-3xl font-bold text-gray-900 mb-8">Kundvagn</h1>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-12 items-start">
                <!-- Cart Items List -->
                <div class="lg:col-span-2 space-y-4">
                    ${cart.map(item => `
                        <div class="bg-white border border-gray-200 rounded-xl p-4 sm:p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
                            <div class="flex items-center space-x-4 w-full sm:w-auto">
                                <img src="${item.image}" alt="${item.name}" class="w-20 h-20 object-cover rounded-lg bg-gray-100 flex-shrink-0">
                                <div>
                                    <h3 class="font-semibold text-gray-900 text-base">${item.name}</h3>
                                    <p class="text-sm text-gray-500 mt-1">${item.price} kr / st</p>
                                </div>
                            </div>
                            <div class="flex items-center justify-between w-full sm:w-auto space-x-6">
                                <div class="flex items-center border border-gray-300 rounded-lg">
                                    <button onclick="updateQuantity(${item.id}, -1)" class="px-3 py-1 text-gray-600 hover:bg-gray-100 transition">-</button>
                                    <span class="px-3 py-1 text-sm font-medium text-gray-900">${item.quantity}</span>
                                    <button onclick="updateQuantity(${item.id}, 1)" class="px-3 py-1 text-gray-600 hover:bg-gray-100 transition">+</button>
                                </div>
                                <span class="font-bold text-gray-900 w-24 text-right">${item.price * item.quantity} kr</span>
                                <button onclick="removeFromCart(${item.id})" class="text-gray-400 hover:text-red-600 transition">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>

                <!-- Order Summary -->
                <div class="bg-gray-50 border border-gray-200 rounded-2xl p-6 space-y-6">
                    <h2 class="text-lg font-bold text-gray-900">Ordersammanfattning</h2>
                    <div class="space-y-3 text-sm text-gray-600">
                        <div class="flex justify-between">
                            <span>Delsumma</span>
                            <span class="font-medium text-gray-900">${subtotal} kr</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Frakt</span>
                            <span class="font-medium text-gray-900">${shipping === 0 ? 'Fri frakt' : shipping + ' kr'}</span>
                        </div>
                        ${subtotal < 490 ? `<p class="text-xs text-blue-600">Lägg till ${490 - subtotal} kr till för fri frakt!</p>` : ''}
                        <div class="border-t border-gray-200 pt-3 flex justify-between text-base font-bold text-gray-900">
                            <span>Att betala</span>
                            <span>${total} kr</span>
                        </div>
                    </div>
                    <button onclick="router.navigate('checkout')" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-4 px-6 rounded-xl shadow transition text-center">
                        Gå till kassan
                    </button>
                </div>
            </div>
        </div>
    `;
}

function renderCheckout() {
    if (cart.length === 0) {
        router.navigate('cart');
        return '';
    }

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const shipping = subtotal >= 490 ? 0 : 49;
    const total = subtotal + shipping;

    return `
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <h1 class="text-3xl font-bold text-gray-900 mb-8">Kassa</h1>

            <form onsubmit="handleCheckoutSubmit(event)" class="grid grid-cols-1 lg:grid-cols-3 gap-12 items-start">
                <!-- Checkout Form -->
                <div class="lg:col-span-2 space-y-8">
                    <div class="bg-white border border-gray-200 rounded-2xl p-6 sm:p-8 space-y-6">
                        <h2 class="text-xl font-bold text-gray-900">1. Leveransinformation</h2>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div class="sm:col-span-2">
                                <label class="block text-sm font-medium text-gray-700 mb-1">Fullständigt namn</label>
                                <input type="text" name="name" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600">
                            </div>
                            <div class="sm:col-span-2">
                                <label class="block text-sm font-medium text-gray-700 mb-1">E-postadress</label>
                                <input type="email" name="email" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600">
                            </div>
                            <div class="sm:col-span-2">
                                <label class="block text-sm font-medium text-gray-700 mb-1">Gatuadress</label>
                                <input type="text" name="address" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Postnummer</label>
                                <input type="text" name="zip" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Stad</label>
                                <input type="text" name="city" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600">
                            </div>
                        </div>
                    </div>

                    <div class="bg-white border border-gray-200 rounded-2xl p-6 sm:p-8 space-y-6">
                        <h2 class="text-xl font-bold text-gray-900">2. Betalningsmetod</h2>
                        <div class="space-y-4">
                            <label class="flex items-center space-x-3 border border-gray-300 p-4 rounded-xl cursor-pointer hover:border-blue-600 transition">
                                <input type="radio" name="paymentMethod" value="Klarna" checked class="text-blue-600 focus:ring-blue-500">
                                <div>
                                    <span class="font-semibold text-gray-900 block">Klarna Betalning</span>
                                    <span class="text-xs text-gray-500">Betala direkt, senare eller dela upp.</span>
                                </div>
                            </label>
                            <label class="flex items-center space-x-3 border border-gray-300 p-4 rounded-xl cursor-pointer hover:border-blue-600 transition">
                                <input type="radio" name="paymentMethod" value="Swish" class="text-blue-600 focus:ring-blue-500">
                                <div>
                                    <span class="font-semibold text-gray-900 block">Swish</span>
                                    <span class="text-xs text-gray-500">Betala direkt med din mobiltelefon.</span>
                                </div>
                            </label>
                            <label class="flex items-center space-x-3 border border-gray-300 p-4 rounded-xl cursor-pointer hover:border-blue-600 transition">
                                <input type="radio" name="paymentMethod" value="Kortbetalning" class="text-blue-600 focus:ring-blue-500">
                                <div>
                                    <span class="font-semibold text-gray-900 block">Kortbetalning (Visa / Mastercard)</span>
                                    <span class="text-xs text-gray-500">Säker kortbetalning via SSL.</span>
                                </div>
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Summary Sidebar -->
                <div class="bg-gray-50 border border-gray-200 rounded-2xl p-6 space-y-6">
                    <h2 class="text-lg font-bold text-gray-900">Din beställning</h2>
                    <div class="space-y-4 max-h-60 overflow-y-auto">
                        ${cart.map(item => `
                            <div class="flex justify-between items-center text-sm">
                                <span class="text-gray-600">${item.name} (x${item.quantity})</span>
                                <span class="font-medium text-gray-900">${item.price * item.quantity} kr</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="border-t border-gray-200 pt-4 space-y-2 text-sm text-gray-600">
                        <div class="flex justify-between">
                            <span>Delsumma</span>
                            <span class="font-medium text-gray-900">${subtotal} kr</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Frakt</span>
                            <span class="font-medium text-gray-900">${shipping === 0 ? 'Fri frakt' : shipping + ' kr'}</span>
                        </div>
                        <div class="border-t border-gray-200 pt-3 flex justify-between text-base font-bold text-gray-900">
                            <span>Att betala</span>
                            <span>${total} kr</span>
                        </div>
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-4 px-6 rounded-xl shadow transition text-center">
                        Slutför köp
                    </button>
                </div>
            </form>
        </div>
    `;
}

function renderOrderSuccess(order) {
    if (!order) {
        router.navigate('home');
        return '';
    }

    return `
        <div class="max-w-3xl mx-auto px-4 py-20 text-center space-y-6">
            <div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto text-green-600">
                <svg class="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
            </div>
            <h1 class="text-3xl sm:text-4xl font-bold text-gray-900">Tack för din beställning!</h1>
            <p class="text-gray-600 max-w-lg mx-auto">Vi har mottagit din order och förbereder den för leverans. En orderbekräftelse har skickats till <span class="font-semibold text-gray-900">${order.email}</span>.</p>
            
            <div class="bg-gray-50 border border-gray-200 rounded-2xl p-6 text-left max-w-md mx-auto space-y-3">
                <div class="flex justify-between text-sm">
                    <span class="text-gray-500">Ordernummer:</span>
                    <span class="font-bold text-gray-900">${order.orderNumber}</span>
                </div>
                <div class="flex justify-between text-sm">
                    <span class="text-gray-500">Datum:</span>
                    <span class="font-medium text-gray-900">${order.date}</span>
                </div>
                <div class="flex justify-between text-sm">
                    <span class="text-gray-500">Betalningsmetod:</span>
                    <span class="font-medium text-gray-900">${order.paymentMethod}</span>
                </div>
                <div class="flex justify-between text-sm border-t border-gray-200 pt-3">
                    <span class="text-gray-500">Totalt belopp:</span>
                    <span class="font-bold text-gray-900">${order.total} kr</span>
                </div>
            </div>

            <div class="pt-4">
                <button onclick="router.navigate('home')" class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3.5 px-8 rounded-lg shadow transition">
                    Tillbaka till startsidan
                </button>
            </div>
        </div>
    `;
}

function renderAbout() {
    return `
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-12">
            <div class="space-y-4 text-center">
                <h1 class="text-3xl sm:text-4xl font-bold text-gray-900">Om NEXORA</h1>
                <p class="text-lg text-gray-600 font-medium">Discover More. Live Better.</p>
            </div>
            <div class="bg-gray-100 rounded-2xl overflow-hidden shadow-md h-[350px]">
                <img src="https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=1000&auto=format&fit=crop" alt="Om Nexora" class="w-full h-full object-cover">
            </div>
            <div class="prose max-w-none text-gray-600 space-y-6 leading-relaxed">
                <p>NEXORA grundades med en tydlig vision: att erbjuda handplockade kvalitetsprodukter som kombinerar skandinavisk design, funktion och hållbarhet. Vi tror på att förenkla vardagen utan att kompromissa med stil eller kvalitet.</p>
                <p>Varje produkt i vårt sortiment är noggrant utvald och testad för att möta högt ställda krav från våra kunder. Vi samarbetar enbart med noggrant granskade tillverkare för att säkerställa högsta möjliga standard.</p>
                <h3 class="text-xl font-bold text-gray-900 pt-4">Våra kärnvärden</h3>
                <ul class="space-y-2 list-disc pl-5">
                    <li><strong class="text-gray-900">Kvalitet i fokus:</strong> Inga kompromisser med materialval och hållbarhet.</li>
                    <li><strong class="text-gray-900">Kundnöjdhet:</strong> Snabb support och trygga köpvillkor.</li>
                    <li><strong class="text-gray-900">Hållbarhet:</strong> Medvetna val för en bättre framtid.</li>
                </ul>
            </div>
        </div>
    `;
}

function renderContact() {
    return `
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-12">
            <div class="space-y-4 text-center">
                <h1 class="text-3xl sm:text-4xl font-bold text-gray-900">Kontakta oss</h1>
                <p class="text-gray-600">Vi finns här för att hjälpa dig med dina frågor och funderingar.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div class="bg-gray-50 border border-gray-200 rounded-2xl p-8 space-y-6">
                    <h2 class="text-xl font-bold text-gray-900">Kundtjänst</h2>
                    <p class="text-gray-600 text-sm leading-relaxed">Har du frågor om din beställning, våra produkter eller något annat? Tveka inte att höra av dig till oss.</p>
                    <div class="space-y-4 text-sm text-gray-600">
                        <div class="flex items-center space-x-3">
                            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                            <span>support@nexora.se</span>
                        </div>
                        <div class="flex items-center space-x-3">
                            <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                            <span>Svarstid: Inom 24 timmar på vardagar</span>
                        </div>
                    </div>
                </div>

                <form onsubmit="event.preventDefault(); showNotification('Tack! Ditt meddelande har skickats.'); this.reset();" class="bg-white border border-gray-200 rounded-2xl p-8 space-y-4">
                    <h2 class="text-xl font-bold text-gray-900">Skicka ett meddelande</h2>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Ditt namn</label>
                        <input type="text" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Din e-post</label>
                        <input type="email" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Meddelande</label>
                        <textarea rows="4" required class="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-gray-900 focus:outline-none focus:border-blue-600"></textarea>
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg shadow transition">
                        Skicka meddelande
                    </button>
                </form>
            </div>
        </div>
    `;
}

function renderTerms() {
    return `
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-8">
            <h1 class="text-3xl font-bold text-gray-900">Köpvillkor</h1>
            <div class="prose max-w-none text-gray-600 space-y-4 leading-relaxed text-sm">
                <p>Välkommen till NEXORA. Genom att handla hos oss godkänner du följande köpvillkor. Vi rekommenderar att du läser igenom villkoren noggrant innan du genomför ett köp.</p>
                <h3 class="text-lg font-bold text-gray-900 pt-2">1. Priser och betalning</h3>
                <p>Alla priser anges i svenska kronor (SEK) inklusive moms. Vi erbjuder säkra betalningslösningar via Klarna, Swish och kortbetalning.</p>
                <h3 class="text-lg font-bold text-gray-900 pt-2">2. Leverans</h3>
                <p>Normal leveranstid är 1-3 arbetsdagar. Fri frakt erbjuds på beställningar över 490 kr.</p>
                <h3 class="text-lg font-bold text-gray-900 pt-2">3. Garanti</h3>
                <p>Vi lämnar 1 års produktgaranti på samtliga produkter i enlighet med svensk konsumentköplag.</p>
            </div>
        </div>
    `;
}

function renderReturns() {
    return `
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-8">
            <h1 class="text-3xl font-bold text-gray-900">Returer & Byte</h1>
            <div class="prose max-w-none text-gray-600 space-y-4 leading-relaxed text-sm">
                <p>Vi vill att du ska vara 100% nöjd med din beställning från NEXORA. Därför erbjuder vi 30 dagars öppet köp från det datum du mottagit dina varor.</p>
                <h3 class="text-lg font-bold text-gray-900 pt-2">Så här gör du en retur:</h3>
                <ol class="list-decimal pl-5 space-y-2">
                    <li>Kontakta vår kundtjänst på support@nexora.se för att få en retursedel.</li>
                    <li>Packa varan väl i sin originalförpackning.</li>
                    <li>Sätt på retursedeln och lämna in paketet hos närmaste ombud.</li>
                </ol>
                <p>När vi har mottagit och godkänt din retur återbetalar vi beloppet inom 3-5 arbetsdagar.</p>
            </div>
        </div>
    `;
}

function renderFaq() {
    return `
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 space-y-8">
            <h1 class="text-3xl font-bold text-gray-900">Vanliga frågor (FAQ)</h1>
            <div class="space-y-6">
                <div class="bg-gray-50 border border-gray-200 rounded-xl p-6">
                    <h3 class="font-bold text-gray-900 text-base mb-2">Hur lång är leveranstiden?</h3>
                    <p class="text-gray-600 text-sm">Normal leveranstid är 1-3 arbetsdagar. Beställningar lagda före 14:00 skickas samma dag.</p>
                </div>
                <div class="bg-gray-50 border border-gray-200 rounded-xl p-6">
                    <h3 class="font-bold text-gray-900 text-base mb-2">Vad kostar frakten?</h3>
                    <p class="text-gray-600 text-sm">Vi erbjuder fri frakt på alla beställningar över 490 kr. För ordrar under 490 kr tillkommer en fraktavgift på 49 kr.</p>
                </div>
                <div class="bg-gray-50 border border-gray-200 rounded-xl p-6">
                    <h3 class="font-bold text-gray-900 text-base mb-2">Hur fungerar öppet köp?</h3>
                    <p class="text-gray-600 text-sm">Du har alltid 30 dagars öppet köp. Produkten ska vara i väsentligen oförändrat skick och i originalförpackning.</p>
                </div>
            </div>
        </div>
    `;
}

document.addEventListener('DOMContentLoaded', () => {
    router.navigate('home');
});