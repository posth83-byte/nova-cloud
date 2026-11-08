const products = [
    {
        id: 1,
        name: "Lumina Trådlös Bordslampa",
        category: "Belysning",
        price: 699,
        sku: "NV-BIL-01",
        stock: 14,
        image: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Uppladdningsbar och dimbar bordslampa i aluminium med mjukt varmvitt ljus.",
        longDesc: "Lumina är skapad för flexibilitet i hemmet. Med steglös dimring, lång batteritid och IP54-klassning fungerar den lika bra på nattduksbordet som på den vindskyddade balkongen. Stilren skandinavisk formgivning som smälter in i alla miljöer."
    },
    {
        id: 2,
        name: "Aura Aromaspridare & Luftfuktare",
        category: "Inredning",
        price: 449,
        sku: "NV-INN-02",
        stock: 22,
        image: "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Ultraljudsdriven aromadiffusor i äkta träfinish med dämpad LED-belysning.",
        longDesc: "Skapa en harmonisk atmosfär med Aura. Den sprider dina favoritoljor tyst och effektivt samtidigt som den tillför diskret fuktighet till torr inomhusluft. Stängs av automatiskt när tanken är tom."
    },
    {
        id: 3,
        name: "Krona Smart Vattenkokare",
        category: "Kök",
        price: 899,
        sku: "NV-KOK-03",
        stock: 8,
        image: "https://images.unsplash.com/photo-1594213728135-e1026a27e3ff?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Precisionstemperatur i borstat stål med appstyrning och varmhållningsläge.",
        longDesc: "För te- och kaffeälskaren. Krona låter dig ställa in exakt vattentemperatur (från 40 till 100 grader) beroende på bryggmetod. Håll-varm-funktionen bibehåller temperaturen i upp till 60 minuter."
    },
    {
        id: 4,
        name: "Terra Minimalistisk Väggklocka",
        category: "Inredning",
        price: 349,
        sku: "NV-INN-04",
        stock: 19,
        image: "https://images.unsplash.com/photo-1563861826100-9cb868fdbe1c?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Tystgående väggklocka med urtavla i mattlackerad stål och trädetaljer.",
        longDesc: "Inga tickande ljud som stör ron. Terra har ett tyst kvartsurverk och en ren, avskalad design som hyllar den skandinaviska designtraditionen. Passar perfekt i kök, hall eller arbetsrum."
    },
    {
        id: 5,
        name: "Nexus Smart Laddstation",
        category: "Smart Hem",
        price: 599,
        sku: "NV-SMA-05",
        stock: 30,
        image: "https://images.unsplash.com/photo-1616440347437-b1c73416efc2?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Trådlös 3-i-1 laddstation för telefon, hörlurar och smartwatch i ekdesign.",
        longDesc: "Bli kvitt trassel på skrivbordet eller nattduksbordet. Nexus laddar alla dina dagliga enheter samtidigt med snabb Qi-laddning och överhettningsskydd. Klädd i slitstark ek och mjukt tyg."
    },
    {
        id: 6,
        name: "Nordic Breeze Bordsfläkt",
        category: "Smart Hem",
        price: 799,
        sku: "NV-SMA-06",
        stock: 11,
        image: "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Tyst och oscillerande bordsfläkt med läderhandtag och USB-C-laddning.",
        longDesc: "Svalt och snyggt under varma sommardagar eller instängda kontorskvällar. Nordic Breeze erbjuder fyra hastighetslägen, extremt tyst drift och ett elegant bärhandtag i vegetabiliskt garvat läder."
    },
    {
        id: 7,
        name: "Vera Keramisk Kaffebryggare",
        category: "Kök",
        price: 399,
        sku: "NV-KOK-07",
        stock: 25,
        image: "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Pour-over drifta i handgjord stengods-keramik med matchande serveringskanna.",
        longDesc: "Upptäck konsten att brygga handgjort kaffe. Vera-kannan och filtret i glaserad stengods håller värmen optimalt under extraktionen och ger en ren, fyllig smakprofil till morgonkoppen."
    },
    {
        id: 8,
        name: "Solros Wake-up Ljusväckarklocka",
        category: "Belysning",
        price: 849,
        sku: "NV-BIL-08",
        stock: 16,
        image: "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Simulerar soluppgång för ett naturligt och behagligt uppvaknande med naturljud.",
        longDesc: "Vakna utvilad utan stressande pipljud. Solros ökar ljusstyrkan gradvis under 30 minuter innan alarmet ringer, kompletterat med lugnande naturimitationer som fågelkvitter eller vågskvalp."
    },
    {
        id: 9,
        name: "Fjord Termosflaska 0.7L",
        category: "Kök",
        price: 299,
        sku: "NV-KOK-09",
        stock: 40,
        image: "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Dubbelväggig vakuumflaska i rostfritt stål som håller kyla i 24h och värme i 12h.",
        longDesc: "Fjord följer med dig till jobbet, gymmet eller fjällvandringen. 100% läckagesäker, kondensfri yta och pulverlackerad utsida som ger ett säkert grepp i alla väder."
    },
    {
        id: 10,
        name: "Echo Smart Inomhussensor",
        category: "Smart Hem",
        price: 349,
        sku: "NV-SMA-10",
        stock: 18,
        image: "https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Trådlös mätare för temperatur, luftfuktighet och koldioxid med e-paper-skärm.",
        longDesc: "Ha full koll på inomhusklimatet. Echo drivs av lågenergi-teknik, visar data tydligt på skärmen och skickar notiser till din telefon om ventilationen behöver ses över."
    },
    {
        id: 11,
        name: "Hugin Elektrisk Salt- & Pepparkvarn",
        category: "Kök",
        price: 499,
        sku: "NV-KOK-11",
        stock: 15,
        image: "https://images.unsplash.com/photo-1588854337236-6889d631faa8?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Enhandsbetjänt kvarn med keramiskt malverk och inbyggd LED-belysning.",
        longDesc: "Kvalitet i varje måltid. Hugin har ett ställbart keramiskt malverk som klarar både grovt havssalt och torkade kryddor. Drivs av batterier och tänds automatiskt i botten när du lutar den över tallriken."
    },
    {
        id: 12,
        name: "Nordic Leaf Ullpläd",
        category: "Inredning",
        price: 999,
        sku: "NV-INN-12",
        stock: 9,
        image: "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Handvävd pläd i 100% lammull med klassiskt mönster och fransar.",
        longDesc: "Värm dig under kyliga kvällar med en exklusiv ullpläd från Nordic Leaf. Lammullen är naturligt smutsavvisande, otroligt mjuk mot huden och skapar en ombonad känsla i soffan eller fåtöljen."
    },
    {
        id: 13,
        name: "Zenith Golvlampa i Matt Metall",
        category: "Belysning",
        price: 1499,
        sku: "NV-BIL-13",
        stock: 5,
        image: "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Elegant läslampa med riktbart huvud och fot i tung marmor.",
        longDesc: "Zenith är belysning när den är som mest skulptural. Den tunga marmorfoten ger stabilitet åt den slanka armen som kan vinklas exakt dit du behöver läsljus i läshörnan."
    },
    {
        id: 14,
        name: "Kust Handtvålpump & Fat i Stengods",
        category: "Inredning",
        price: 279,
        sku: "NV-INN-14",
        stock: 28,
        image: "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Tvålpump med rostfri pumpmekanism och tillhörande litet fat i keramik.",
        longDesc: "Lyft detaljerna i badrummet eller köket. Kust-serien i oglaserad stengods har en behaglig naturkänsla och står stabilt på handfatet utan att glida."
    },
    {
        id: 15,
        name: "Nova Smart Vägguttag med Energiövervakning",
        category: "Smart Hem",
        price: 249,
        sku: "NV-SMA-15",
        stock: 35,
        image: "https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Styr dina apparater via app och håll koll på strömförbrukningen i realtid.",
        longDesc: "Minska energislöseriet i hemmet. Nova kopplas upp direkt till ditt Wi-Fi utan hubb. Sätt timers, schemalägg kaffebryggaren eller stäng av glömda strykjärn direkt från mobilen."
    },
    {
        id: 16,
        name: "Atlas Skärbräda i Ädelträ",
        category: "Kök",
        price: 549,
        sku: "NV-KOK-16",
        stock: 12,
        image: "https://images.unsplash.com/photo-1590736969955-71cc94901055?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Ändträskärbräda i hållbar europeisk ek med saftspår och handtag.",
        longDesc: "En skärbräda som är skonsam mot dina knivseggar och vacker nog att ställa fram som serveringsbricka för ost och chark. Behandlad med livsmedelsgodkänd olja."
    },
    {
        id: 17,
        name: "Borealis Nattlampa med Rörelsesensor",
        category: "Belysning",
        price: 199,
        sku: "NV-BIL-17",
        stock: 24,
        image: "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Magnetisk vägglampa i trä med mjukt sken för hall och trapphus.",
        longDesc: "Smidigt nattljus som tänds automatiskt när rörelse detekteras i mörker. Fästs enkelt med medföljande magnetfäste så att du kan ta loss lampan och använda som ficklampa vid behov."
    },
    {
        id: 18,
        name: "Lager Minimalistisk Magasinhållare",
        category: "Inredning",
        price: 649,
        sku: "NV-INN-18",
        stock: 10,
        image: "https://images.unsplash.com/photo-1544457070-4cd773b4d71e?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Tidningsställ i pulverlackerad ståltråd och läderdetaljer.",
        longDesc: "Håll ordning på favorittidningar, böcker eller anteckningsblock. Lager förenar industriell stålkonstruktion med mjuka läderremmar för ett genuint skandinaviskt uttryck."
    },
    {
        id: 19,
        name: "Strata Digital Kökshushållsvåg",
        category: "Kök",
        price: 329,
        sku: "NV-KOK-19",
        stock: 20,
        image: "https://images.unsplash.com/photo-1589365278144-c9e705f9cf3ba?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Tunn köksvåg i härdat glas med LCD-display och hög precision.",
        longDesc: "För ett lyckat bakresultat krävs millimeterprecision. Strata väger upp till 5 kg med 1 grams noggrannhet. Tunn profil som enkelt förvaras i kökslådan."
    },
    {
        id: 20,
        name: "Nimbus Luftrenare för Mindre Rum",
        category: "Smart Hem",
        price: 1299,
        sku: "NV-SMA-20",
        stock: 7,
        image: "https://images.unsplash.com/photo-1585771724684-38269d6639fd?auto=format&fit=crop&w=800&q=80",
        shortDesc: "Kompakt luftrenare med True HEPA-13 filter och tyst nattläge.",
        longDesc: "Andas rent i sovrummet eller hemmakontoret. Nimbus fångar upp 99.97% av damm, pollen och fina partiklar. Utrustad med filterbyteindikator och diskret belysning."
    }
];

// App State
let cart = JSON.parse(localStorage.getItem('nordic_varda_cart')) || [];
let currentCategory = 'all';
let currentSearch = '';
let currentSort = 'default';
let activeModalProduct = null;

// DOM Elements
const productGrid = document.getElementById('product-grid');
const productCountEl = document.getElementById('product-count');
const searchInput = document.getElementById('search-input');
const sortSelect = document.getElementById('sort-select');
const categoryButtons = document.querySelectorAll('.category-btn');
const cartToggleBtn = document.getElementById('cart-toggle-btn');
const mobileMenuBtn = document.getElementById('mobile-menu-btn');
const mobileMenu = document.getElementById('mobile-menu');
const cartDrawer = document.getElementById('cart-drawer');
const cartOverlay = document.getElementById('cart-overlay');
const closeCartBtn = document.getElementById('close-cart');
const cartItemsContainer = document.getElementById('cart-items');
const cartBadge = document.getElementById('cart-badge');
const cartSubtotalEl = document.getElementById('cart-subtotal');
const cartShippingEl = document.getElementById('cart-shipping');
const cartTotalEl = document.getElementById('cart-total');
const freeShippingNotice = document.getElementById('free-shipping-notice');
const freeShippingProgress = document.getElementById('free-shipping-progress');
const checkoutBtn = document.getElementById('checkout-btn');

const productModal = document.getElementById('product-modal');
const modalOverlay = document.getElementById('modal-overlay');
const closeModalBtn = document.getElementById('close-modal');
const modalImage = document.getElementById('modal-image');
const modalCategory = document.getElementById('modal-category');
const modalTitle = document.getElementById('modal-title');
const modalPrice = document.getElementById('modal-price');
const modalSku = document.getElementById('modal-sku');
const modalStock = document.getElementById('modal-stock');
const modalDesc = document.getElementById('modal-desc');
const modalQtyInput = document.getElementById('modal-qty');
const modalAddToCartBtn = document.getElementById('modal-add-to-cart');

const checkoutModal = document.getElementById('checkout-modal');
const checkoutOverlay = document.getElementById('checkout-overlay');
const closeCheckoutBtn = document.getElementById('close-checkout');
const checkoutForm = document.getElementById('checkout-form');
const checkoutSuccess = document.getElementById('checkout-success');
const orderNumberEl = document.getElementById('order-number');
const closeSuccessBtn = document.getElementById('close-success');

const cookieBanner = document.getElementById('cookie-banner');
const acceptCookiesBtn = document.getElementById('accept-cookies');
const contactForm = document.getElementById('contact-form');
const newsletterForm = document.getElementById('newsletter-form');

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    renderProducts();
    updateCartUI();
    setupEventListeners();
    checkCookies();
});

function setupEventListeners() {
    // Search input
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase().trim();
            renderProducts();
        });
    }

    // Sort select
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            currentSort = e.target.value;
            renderProducts();
        });
    }

    // Category buttons
    categoryButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            categoryButtons.forEach(b => {
                b.classList.remove('accent-bg', 'text-white');
                b.classList.add('bg-[#EAE5DE]', 'text-[#1C1E21]');
            });
            const target = e.currentTarget;
            target.classList.remove('bg-[#EAE5DE]', 'text-[#1C1E21]');
            target.classList.add('accent-bg', 'text-white');

            currentCategory = target.getAttribute('data-category');
            renderProducts();
        });
    });

    // Mobile menu toggle
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
        mobileMenu.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => mobileMenu.classList.add('hidden'));
        });
    }

    // Cart drawer toggle
    if (cartToggleBtn && cartDrawer && cartOverlay) {
        cartToggleBtn.addEventListener('click', openCart);
        closeCartBtn.addEventListener('click', closeCart);
        cartOverlay.addEventListener('click', closeCart);
    }

    // Modal close
    if (closeModalBtn && modalOverlay) {
        closeModalBtn.addEventListener('click', closeModal);
        modalOverlay.addEventListener('click', closeModal);
    }

    // Checkout modal toggle
    if (checkoutBtn && checkoutModal) {
        checkoutBtn.addEventListener('click', () => {
            if (cart.length === 0) {
                alert('Din varukorg är tom.');
                return;
            }
            closeCart();
            openCheckout();
        });
        closeCheckoutBtn.addEventListener('click', closeCheckout);
        checkoutOverlay.addEventListener('click', closeCheckout);
        closeSuccessBtn.addEventListener('click', () => {
            checkoutSuccess.classList.add('hidden');
            checkoutForm.classList.remove('hidden');
            closeCheckout();
        });
    }

    // Checkout form submit
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const formData = new FormData(checkoutForm);
            // Validation check handled by HTML required attributes, simulate success order
            const orderId = 'NV-' + Math.floor(100000 + Math.random() * 900000);
            orderNumberEl.textContent = orderId;
            
            checkoutForm.classList.add('hidden');
            checkoutSuccess.classList.remove('hidden');

            // Clear cart
            cart = [];
            saveCart();
            updateCartUI();
            checkoutForm.reset();
        });
    }

    // Cookie consent
    if (acceptCookiesBtn && cookieBanner) {
        acceptCookiesBtn.addEventListener('click', () => {
            localStorage.setItem('nordic_varda_cookies', 'accepted');
            cookieBanner.classList.add('hidden');
        });
    }

    // Contact form
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Tack för ditt meddelande! Vi återkommer inom 24 timmar.');
            contactForm.reset();
        });
    }

    // Newsletter form
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            alert('Tack för din prenumeration! En rabattkod på 10% har skickats till din e-post.');
            newsletterForm.reset();
        });
    }

    // Modal Add To Cart
    if (modalAddToCartBtn) {
        modalAddToCartBtn.addEventListener('click', () => {
            if (!activeModalProduct) return;
            const qty = parseInt(modalQtyInput.value) || 1;
            addToCart(activeModalProduct.id, qty);
            closeModal();
            openCart();
        });
    }
}

function checkCookies() {
    if (localStorage.getItem('nordic_varda_cookies') === 'accepted') {
        if (cookieBanner) cookieBanner.classList.add('hidden');
    }
}

// Product Filtering & Sorting
function getFilteredAndSortedProducts() {
    let result = [...products];

    // Category filter
    if (currentCategory !== 'all') {
        result = result.filter(p => p.category === currentCategory);
    }

    // Search filter
    if (currentSearch !== '') {
        result = result.filter(p => 
            p.name.toLowerCase().includes(currentSearch) ||
            p.shortDesc.toLowerCase().includes(currentSearch) ||
            p.category.toLowerCase().includes(currentSearch)
        );
    }

    // Sorting
    if (currentSort === 'price-asc') {
        result.sort((a, b) => a.price - b.price);
    } else if (currentSort === 'price-desc') {
        result.sort((a, b) => b.price - a.price);
    } else if (currentSort === 'name-asc') {
        result.sort((a, b) => a.name.localeCompare(b.name, 'sv'));
    }

    return result;
}

function renderProducts() {
    if (!productGrid) return;
    const filtered = getFilteredAndSortedProducts();
    productCountEl.textContent = `${filtered.length} st produkter`;

    if (filtered.length === 0) {
        productGrid.innerHTML = `
            <div class="col-span-full py-16 text-center">
                <p class="text-lg text-[#5A5E63]">Inga produkter matchade din sökning.</p>
                <button onclick="resetFilters()" class="mt-4 px-6 py-2 bg-[#1C1E21] text-white text-sm rounded-lg hover:bg-[#A95C42] transition-colors">Återställ filter</button>
            </div>
        `;
        return;
    }

    productGrid.innerHTML = filtered.map(product => `
        <div class="bg-white rounded-2xl border border-[#EAE5DE] overflow-hidden group flex flex-col justify-between transition-all hover:shadow-lg">
            <div>
                <div class="relative aspect-[4/3] bg-[#EAE5DE] overflow-hidden cursor-pointer" onclick="openModal(${product.id})">
                    <img src="${product.image}" alt="${product.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80'">
                    <span class="absolute top-3 left-3 bg-[#FBF9F5]/90 backdrop-blur-sm text-[#1C1E21] text-xs font-semibold px-2.5 py-1 rounded-full">
                        ${product.category}
                    </span>
                </div>
                <div class="p-5 space-y-2">
                    <h3 class="font-bold text-lg text-[#1C1E21] cursor-pointer hover:text-[#A95C42] transition-colors line-clamp-1" onclick="openModal(${product.id})">
                        ${product.name}
                    </h3>
                    <p class="text-sm text-[#5A5E63] line-clamp-2">
                        ${product.shortDesc}
                    </p>
                </div>
            </div>
            <div class="p-5 pt-0 flex items-center justify-between border-t border-[#EAE5DE]/50 mt-4">
                <div>
                    <span class="text-xs text-[#5A5E63] block">Pris (Demo)</span>
                    <span class="text-lg font-bold text-[#1C1E21]">${product.price} SEK</span>
                </div>
                <div class="flex space-x-2">
                    <button onclick="openModal(${product.id})" class="p-2.5 rounded-xl border border-[#EAE5DE] hover:border-[#1C1E21] transition-colors" title="Visa detaljer" aria-label="Visa detaljer">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-[#1C1E21]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                    </button>
                    <button onclick="addToCart(${product.id})" class="accent-bg accent-hover text-white px-4 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-sm">
                        Köp
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function resetFilters() {
    currentCategory = 'all';
    currentSearch = '';
    currentSort = 'default';
    if (searchInput) searchInput.value = '';
    if (sortSelect) sortSelect.value = 'default';
    categoryButtons.forEach(b => {
        if (b.getAttribute('data-category') === 'all') {
            b.classList.remove('bg-[#EAE5DE]', 'text-[#1C1E21]');
            b.classList.add('accent-bg', 'text-white');
        } else {
            b.classList.remove('accent-bg', 'text-white');
            b.classList.add('bg-[#EAE5DE]', 'text-[#1C1E21]');
        }
    });
    renderProducts();
}

// Modal Functions
function openModal(productId) {
    const product = products.find(p => p.id === productId);
    if (!product) return;
    activeModalProduct = product;

    modalImage.src = product.image;
    modalImage.onerror = () => { modalImage.src = 'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80'; };
    modalCategory.textContent = product.category;
    modalTitle.textContent = product.name;
    modalPrice.textContent = `${product.price} SEK`;
    modalSku.textContent = product.sku;
    modalStock.textContent = `${product.stock} st i lager`;
    modalDesc.textContent = product.longDesc;
    modalQtyInput.value = 1;

    productModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    productModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
    activeModalProduct = null;
}

// Cart Functions
function openCart() {
    cartDrawer.classList.remove('translate-x-full');
    cartOverlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeCart() {
    cartDrawer.classList.add('translate-x-full');
    cartOverlay.classList.add('hidden');
    document.body.style.overflow = 'auto';
}

function addToCart(productId, quantity = 1) {
    const product = products.find(p => p.id === productId);
    if (!product) return;

    const existingItem = cart.find(item => item.id === productId);
    if (existingItem) {
        existingItem.quantity += quantity;
    } else {
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            quantity: quantity,
            sku: product.sku
        });
    }

    saveCart();
    updateCartUI();
    openCart();
}

function removeFromCart(productId) {
    cart = cart.filter(item => item.id !== productId);
    saveCart();
    updateCartUI();
}

function updateQuantity(productId, delta) {
    const item = cart.find(i => i.id === productId);
    if (!item) return;
    item.quantity += delta;
    if (item.quantity <= 0) {
        removeFromCart(productId);
    } else {
        saveCart();
        updateCartUI();
    }
}

function saveCart() {
    localStorage.setItem('nordic_varda_cart', JSON.stringify(cart));
}

function updateCartUI() {
    const totalCount = cart.reduce((sum, item) => sum + item.quantity, 0);
    cartBadge.textContent = totalCount;

    if (cart.length === 0) {
        cartItemsContainer.innerHTML = `
            <div class="py-12 text-center text-[#5A5E63]">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12  mx-auto mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                <p>Din varukorg är tom.</p>
            </div>
        `;
        cartSubtotalEl.textContent = '0 SEK';
        cartShippingEl.textContent = '0 SEK';
        cartTotalEl.textContent = '0 SEK';
        if (freeShippingNotice) freeShippingNotice.innerHTML = `Lägg till produkter för <span class="font-bold">500 SEK</span> till för fri frakt!`;
        if (freeShippingProgress) freeShippingProgress.style.width = '0%';
        return;
    }

    cartItemsContainer.innerHTML = cart.map(item => `
        <div class="flex items-center space-x-4 py-4 border-b border-[#EAE5DE]">
            <img src="${item.image}" alt="${item.name}" class="w-16 h-16 object-cover rounded-xl bg-[#EAE5DE]" onerror="this.src='https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=200&q=80'">
            <div class="flex-grow">
                <h4 class="font-bold text-sm text-[#1C1E21] line-clamp-1">${item.name}</h4>
                <span class="text-xs text-[#5A5E63]">${item.price} SEK / st</span>
                <div class="flex items-center space-x-3 mt-2">
                    <div class="flex items-center border border-[#EAE5DE] rounded-lg">
                        <button onclick="updateQuantity(${item.id}, -1)" class="px-2.5 py-1 text-sm hover:bg-[#EAE5DE]/50 transition-colors" aria-label="Minska antal">-</button>
                        <span class="px-2.5 py-1 text-sm font-semibold">${item.quantity}</span>
                        <button onclick="updateQuantity(${item.id}, 1)" class="px-2.5 py-1 text-sm hover:bg-[#EAE5DE]/50 transition-colors" aria-label="Öka antal">+</button>
                    </div>
                    <button onclick="removeFromCart(${item.id})" class="text-xs text-red-600 hover:underline">Ta bort</button>
                </div>
            </div>
            <div class="text-right">
                <span class="font-bold text-sm text-[#1C1E21]">${item.price * item.quantity} SEK</span>
            </div>
        </div>
    `).join('');

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const shipping = subtotal >= 500 || subtotal === 0 ? 0 : 49;
    const total = subtotal + shipping;

    cartSubtotalEl.textContent = `${subtotal} SEK`;
    cartShippingEl.textContent = shipping === 0 ? 'Fri frakt' : `${shipping} SEK`;
    cartTotalEl.textContent = `${total} SEK`;

    const freeShippingThreshold = 500;
    const diff = freeShippingThreshold - subtotal;
    const progressPercent = Math.min(100, (subtotal / freeShippingThreshold) * 100);

    if (freeShippingProgress) freeShippingProgress.style.width = `${progressPercent}%`;

    if (freeShippingNotice) {
        if (diff > 0) {
            freeShippingNotice.innerHTML = `Lägg till för <span class="font-bold">${diff} SEK</span> till för att få fri frakt!`;
        } else {
            freeShippingNotice.innerHTML = `<span class="font-bold text-[#A95C42]">Grattis! Du har uppnått fri frakt.</span>`;
        }
    }
}

// Checkout Functions
function openCheckout() {
    checkoutModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeCheckout() {
    checkoutModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
}