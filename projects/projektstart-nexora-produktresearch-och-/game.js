document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

const products = [
    {
        id: 1,
        name: "LuminaGlow LED-ansiktsmask",
        category: "Skönhet & Hälsa",
        price: 799,
        originalPrice: 1299,
        image: "https://images.unsplash.com/photo-1512290900722-9a702082b2d5?auto=format&fit=crop&w=800&q=80",
        description: "Avancerad fototerapi med LED-ljus för hemmabruk som stimulerar kollagen, reducerar orenheter och ger huden ett strålande lyster.",
        rating: 4.8,
        reviews: 142
    },
    {
        id: 2,
        name: "Zenith Gravity Pro Massagepistol",
        category: "Sport & Träning",
        price: 899,
        originalPrice: 1499,
        image: "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80",
        description: "Kraftfull och tystgående massagepistol med 6 utbytbara huvuden och 30 hastighetslägen för djupgående muskelåterhämtning.",
        rating: 4.9,
        reviews: 218
    },
    {
        id: 3,
        name: "AuraGlow Smart Solnedgångslampa",
        category: "Hem & Inredning",
        price: 349,
        originalPrice: 599,
        image: "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?auto=format&fit=crop&w=800&q=80",
        description: "Skapa en magisk och harmonisk atmosfär i rummet med RGB-styrd solnedgångslampa som styrs via fjärrkontroll eller mobilapp.",
        rating: 4.7,
        reviews: 95
    },
    {
        id: 4,
        name: "NovaPure Mini Luftfuktare",
        category: "Hem & Inredning",
        price: 299,
        originalPrice: 499,
        image: "https://images.unsplash.com/photo-1585771724684-38269d6639fd?auto=format&fit=crop&w=800&q=80",
        description: "Kompakt ultraljudsluftfuktare med inbyggd stämningsbelysning och aromaterapifunktion för förbättrat inomhusklimat.",
        rating: 4.6,
        reviews: 84
    },
    {
        id: 5,
        name: "FlexiGrip Trådlös Laddningsstation 3-i-1",
        category: "Elektronik",
        price: 599,
        originalPrice: 899,
        image: "https://images.unsplash.com/photo-1622445275576-721325763cb4?auto=format&fit=crop&w=800&q=80",
        description: "Ladda din smartphone, smartwatch och trådlösa hörlurar samtidigt på ett stilrent och kompakt ställ utan trassel.",
        rating: 4.9,
        reviews: 310
    },
    {
        id: 6,
        name: "HydroFlask Termosflaska med LED-temperatur",
        category: "Sport & Träning",
        price: 329,
        originalPrice: 499,
        image: "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=800&q=80",
        description: "Håll drycken kall i 24 timmar eller varm i 12 timmar. Inbyggd LED-display på locket visar exakt vätsketemperatur.",
        rating: 4.7,
        reviews: 112
    },
    {
        id: 7,
        name: "CyberShield RFID-Skyddad Plånbok i Kolfiber",
        category: "Mode & Accessoarer",
        price: 399,
        originalPrice: 649,
        image: "https://images.unsplash.com/photo-1627123424574-724758594e93?auto=format&fit=crop&w=800&q=80",
        description: "Minimalistisk korthållare i äkta kolfiber med mekanisk korthantering och certifierat skydd mot korts skimming.",
        rating: 4.8,
        reviews: 178
    },
    {
        id: 8,
        name: "PulseFit Smart Aktivitetsarmband",
        category: "Sport & Träning",
        price: 499,
        originalPrice: 799,
        image: "https://images.unsplash.com/photo-1575311373937-040b8e1fd5b6?auto=format&fit=crop&w=800&q=80",
        description: "Håll koll på hälsan med pulsmätare, blodsyre, sömnanalys och träningslägen i en vattentät och slimmad design.",
        rating: 4.5,
        reviews: 89
    },
    {
        id: 9,
        name: "LuminaStrip Pro RGB LED-lister 10m",
        category: "Hem & Inredning",
        price: 379,
        originalPrice: 599,
        image: "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=800&q=80",
        description: "Musiksynkade LED-lister med miljoner färgnyanser för att lyfta gaminghörnan eller vardagsrummet till nya nivåer.",
        rating: 4.7,
        reviews: 204
    },
    {
        id: 10,
        name: "SonicGlow Elektrisk Tandborste med UV-fodral",
        category: "Skönhet & Hälsa",
        price: 699,
        originalPrice: 1099,
        image: "https://images.unsplash.com/photo-1559595500-e14e32906d72?auto=format&fit=crop&w=800&q=80",
        description: "Sonicteknologi med 40 000 vibrationer per minut och medföljande reséfodral med inbyggd UV-sterilisering.",
        rating: 4.9,
        reviews: 167
    },
    {
        id: 11,
        name: "NeoShave Professionell Hårtrimmer & Shaver",
        category: "Skönhet & Hälsa",
        price: 499,
        originalPrice: 799,
        image: "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=800&q=80",
        description: "Ergonomisk och exakt trimmer för skägg och hår med titanblad och lång batteritid med USB-snabbladdning.",
        rating: 4.6,
        reviews: 134
    },
    {
        id: 12,
        name: "VortexPro Elektrisk Visp & Mjölkskummare",
        category: "Hem & Inredning",
        price: 249,
        originalPrice: 399,
        image: "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=800&q=80",
        description: "Skapa perfekt sammetslent mjölkskum till din cappuccino eller matcha på några sekunder. Uppladdningsbar med ställ.",
        rating: 4.8,
        reviews: 220
    },
    {
        id: 13,
        name: "GravityShield Magnetiskt Bilfäste med Trådlös Laddning",
        category: "Elektronik",
        price: 399,
        originalPrice: 649,
        image: "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?auto=format&fit=crop&w=800&q=80",
        description: "Säkert och stabilt fäste för ventilationsgallret med automatisk magnetisk centrering och snabb trådlös laddning.",
        rating: 4.7,
        reviews: 156
    },
    {
        id: 14,
        name: "AeroBreeze Hopfällbar Bordfläkt med Batteri",
        category: "Hem & Inredning",
        price: 399,
        originalPrice: 599,
        image: "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?auto=format&fit=crop&w=800&q=80",
        description: "Justerbar och teleskopisk bordsfläkt som kan fällas ihop helt. Perfekt för skrivbordet eller sovrummet under varma dagar.",
        rating: 4.5,
        reviews: 78
    },
    {
        id: 15,
        name: "PulseBeat Trådlösa Sportöronsnäckor",
        category: "Elektronik",
        price: 599,
        originalPrice: 999,
        image: "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=800&q=80",
        description: "Ergonomiska öronproppar med aktiv brusreducering (ANC), kristallklart ljud och upp till 30 timmars total speltid med etui.",
        rating: 4.8,
        reviews: 245
    },
    {
        id: 16,
        name: "LuminaBook Läslampa för Bok",
        category: "Hem & Inredning",
        price: 199,
        originalPrice: 299,
        image: "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=800&q=80",
        description: "Uppladdningsbar klämlampa med varmt och ögonvänligt LED-ljus för kvällsläsning utan att störa omgivningen.",
        rating: 4.9,
        reviews: 188
    },
    {
        id: 17,
        name: "ZenithPosture Justerbart Ryggstöd",
        category: "Skönhet & Hälsa",
        price: 349,
        originalPrice: 549,
        image: "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?auto=format&fit=crop&w=800&q=80",
        description: "Ergonomisk hållningsväst som effektivt motverkar gamnacke och kutrygg vid långvarigt sittande framför datorn.",
        rating: 4.4,
        reviews: 92
    },
    {
        id: 18,
        name: "TerraGlow Solcellsdrivna Trädgårdspotts",
        category: "Hem & Inredning",
        price: 449,
        originalPrice: 699,
        image: "https://images.unsplash.com/photo-1558904541-efa8c4a7e289?auto=format&fit=crop&w=800&q=80",
        description: "Vattentäta solcellslampor med realistisk fladdrande lågeffekt för trädgården, altanen eller balkongen.",
        rating: 4.7,
        reviews: 105
    },
    {
        id: 19,
        name: "CyberDesk Musmatta med RGB & Snabbladdning",
        category: "Elektronik",
        price: 429,
        originalPrice: 699,
        image: "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=800&q=80",
        description: "Extra stor gamingmusmatta med vattentålig yta, stämningsfulla RGB-kanter och integrerad trådlös snabbladdningszon.",
        rating: 4.6,
        reviews: 115
    },
    {
        id: 20,
        name: "FlexiFit Träningsband Set 5 delar",
        category: "Sport & Träning",
        price: 299,
        originalPrice: 499,
        image: "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80",
        description: "Komplett paket med motståndsband i slitstark naturlatex för effektiv styrketräning hemma eller på resande fot.",
        rating: 4.9,
        reviews: 302
    }
];

let cart = [];
let currentCategory = 'all';

function initializeApp() {
    renderFeaturedProducts();
    renderShopProducts();
    updateCartUI();
}

function switchView(viewId) {
    document.querySelectorAll('.view-section').forEach(el => {
        el.classList.add('hidden');
    });
    const target = document.getElementById(`view-${viewId}`);
    if (target) {
        target.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

function toggleCart() {
    const drawer = document.getElementById('cart-drawer');
    if (drawer) {
        drawer.classList.toggle('translate-x-full');
    }
}

function renderFeaturedProducts() {
    const container = document.getElementById('featured-products');
    if (!container) return;
    
    const featured = products.slice(0, 4);
    container.innerHTML = featured.map(p => createProductCard(p)).join('');
}

function renderShopProducts() {
    const container = document.getElementById('shop-products');
    if (!container) return;

    let filtered = products;
    if (currentCategory !== 'all') {
        filtered = products.filter(p => p.category === currentCategory);
    }

    container.innerHTML = filtered.map(p => createProductCard(p)).join('');
}

function filterCategory(category) {
    currentCategory = category;
    
    document.querySelectorAll('.cat-btn').forEach(btn => {
        if (btn.dataset.category === category) {
            btn.className = "cat-btn bg-cyan-500 text-black px-5 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-lg shadow-cyan-500/20";
        } else {
            btn.className = "cat-btn bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 px-5 py-2.5 rounded-xl font-medium text-sm transition-all";
        }
    });

    renderShopProducts();
}

function createProductCard(p) {
    return `
        <div class="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden group hover:border-cyan-500/50 transition-all flex flex-col justify-between">
            <div>
                <div class="relative overflow-hidden aspect-square bg-slate-950">
                    <img src="${p.image}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500">
                    <span class="absolute top-3 left-3 bg-slate-950/80 backdrop-blur-md text-cyan-400 text-xs font-semibold px-2.5 py-1 rounded-lg border border-slate-800">
                        ${p.category}
                    </span>
                    <span class="absolute top-3 right-3 bg-cyan-500 text-black text-xs font-bold px-2 py-1 rounded-lg">
                        -${Math.round((1 - p.price / p.originalPrice) * 100)}%
                    </span>
                </div>
                <div class="p-5">
                    <div class="flex items-center space-x-1 text-amber-400 text-xs mb-2">
                        <span>★</span>
                        <span class="text-slate-300 font-semibold">${p.rating}</span>
                        <span class="text-slate-500">(${p.reviews} omdömen)</span>
                    </div>
                    <h3 class="font-heading font-bold text-lg text-white mb-2 line-clamp-1">${p.name}</h3>
                    <p class="text-slate-400 text-xs mb-4 line-clamp-2">${p.description}</p>
                </div>
            </div>
            <div class="p-5 pt-0 flex items-center justify-between">
                <div>
                    <span class="text-xs text-slate-500 line-through block">${p.originalPrice} kr</span>
                    <span class="font-heading font-extrabold text-xl text-cyan-400">${p.price} kr</span>
                </div>
                <button onclick="addToCart(${p.id})" class="bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-bold px-4 py-2.5 rounded-xl text-sm transition-all shadow-lg shadow-cyan-500/20 active:scale-95">
                    Köp nu
                </button>
            </div>
        </div>
    `;
}

function addToCart(productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;

    const existingItem = cart.find(item => item.id === productId);
    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({ ...product, quantity: 1 });
    }

    updateCartUI();
    
    const drawer = document.getElementById('cart-drawer');
    if (drawer && drawer.classList.contains('translate-x-full')) {
        toggleCart();
    }
}

function updateQuantity(productId, delta) {
    const item = cart.find(i => i.id === productId);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
        cart = cart.filter(i => i.id !== productId);
    }

    updateCartUI();
}

function updateCartUI() {
    const badge = document.getElementById('cart-badge');
    const itemsContainer = document.getElementById('cart-items');
    const subtotalEl = document.getElementById('cart-subtotal');
    const shippingEl = document.getElementById('cart-shipping');
    const totalEl = document.getElementById('cart-total');
    const checkoutBtn = document.getElementById('checkout-btn');

    const totalCount = cart.reduce((sum, i) => sum + i.quantity, 0);
    if (badge) badge.innerText = totalCount;

    if (!itemsContainer) return;

    if (cart.length === 0) {
        itemsContainer.innerHTML = `
            <div class="text-center py-12 text-slate-500">
                <svg class="w-16 h-16 mx-auto mb-4 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path>
                </svg>
                <p class="text-sm">Din varukorg är tom.</p>
            </div>
        `;
        if (subtotalEl) subtotalEl.innerText = '0 kr';
        if (shippingEl) shippingEl.innerText = '0 kr';
        if (totalEl) totalEl.innerText = '0 kr';
        if (checkoutBtn) checkoutBtn.disabled = true;
        return;
    }

    if (checkoutBtn) checkoutBtn.disabled = false;

    itemsContainer.innerHTML = cart.map(item => `
        <div class="flex items-center space-x-4 bg-slate-900 border border-slate-800 p-3 rounded-xl">
            <img src="${item.image}" alt="${item.name}" class="w-16 h-16 object-cover rounded-lg bg-slate-950">
            <div class="flex-grow">
                <h4 class="font-heading font-bold text-sm text-white line-clamp-1">${item.name}</h4>
                <p class="text-cyan-400 font-semibold text-sm mb-2">${item.price} kr</p>
                <div class="flex items-center space-x-2">
                    <button onclick="updateQuantity(${item.id}, -1)" class="w-7 h-7 bg-slate-800 rounded-lg text-slate-300 hover:bg-slate-700">-</button>
                    <span class="text-sm font-semibold text-white px-2">${item.quantity}</span>
                    <button onclick="updateQuantity(${item.id}, 1)" class="w-7 h-7 bg-slate-800 rounded-lg text-slate-300 hover:bg-slate-700">+</button>
                </div>
            </div>
            <button onclick="updateQuantity(${item.id}, -${item.quantity})" class="text-slate-500 hover:text-red-400 p-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
            </button>
        </div>
    `).join('');

    const subtotal = cart.reduce((sum, i) => sum + (i.price * i.quantity), 0);
    const shipping = subtotal >= 499 || subtotal === 0 ? 0 : 49;
    const total = subtotal + shipping;

    if (subtotalEl) subtotalEl.innerText = `${subtotal} kr`;
    if (shippingEl) shippingEl.innerText = shipping === 0 ? 'Fri frakt' : `${shipping} kr`;
    if (totalEl) totalEl.innerText = `${total} kr`;
}

function proceedToCheckout() {
    if (cart.length === 0) return;
    toggleCart();
    switchView('checkout');
}

function handleCheckoutSubmit(e) {
    e.preventDefault();
    
    const email = document.getElementById('checkout-email').value;
    const name = document.getElementById('checkout-name').value;
    const address = document.getElementById('checkout-address').value;
    const city = document.getElementById('checkout-city').value;
    const postal = document.getElementById('checkout-postal').value;

    if (!email || !name || !address || !city || !postal) {
        alert('Vänligen fyll i alla fylliga leveransuppgifter.');
        return;
    }

    const orderNumber = 'NX-' + Math.floor(100000 + Math.random() * 900000);
    
    document.getElementById('conf-ordernumber').innerText = orderNumber;
    document.getElementById('conf-email').innerText = email;

    cart = [];
    updateCartUI();
    switchView('confirmation');
}