let products = [
    {
        id: 1,
        name: "Lumina Trådlös Bordslampa",
        category: "Belysning",
        price: 699,
        sku: "NV-BIL-01",
        stock: 14,
        image: "https://sakringt.com/cdn/shop/files/95.png?v=1768472208",
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
        image: "https://web1.wd-plus.de/ebay/A/303751/1.jpg",
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
        image: "https://jo-cell.com/cdn/shop/files/1887_selectionwk_2200_ambiente01_1400px.jpg.thumb.jpg?v=1717924858&width=1400",
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
        image: "https://assets.wfcdn.com/im/35579336/resize-h800-w800%5Ecompr-r85/2987/298754158/Lemnos%2BCARVED%2B-%2BC%2BClock.jpg",
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
        image: "https://i5.walmartimages.com/seo/15W-3-in-1-Wireless-Charging-Station-IPhone-Apple-Watch-AirPods-Magnetic-Adjustable-Angle-Foldable-Design-Night-Light-Overcharge-Protection-White_a1edbaa6-88d3-4e8e-aeff-822b43dd57fd.b898ccbe8f0f0137da4caf5d96301ed9.jpeg",
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
        image: "https://img.muji.com.cn/img/item/4550512851127_07_1260.jpg",
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
        image: "https://images.nexusapp.co/assets/b0/d9/0b/172211644.jpg",
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
        image: "https://www.saatva.com/blog/wp-content/uploads/2025/03/circadian-lighting-mom-cozy-sunrise-alarm-clock-733x800.jpg",
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
        image: "https://www.fluidbranding.ie/media/catalog/product/cache/5d8e184087b91b8c6788f82b1ec6b2b1/1/0/10069381_2.jpg",
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
        image: "https://ikeagreece.akamaized.net/images/1860x1860/variantimages/00498231/0.JPG",
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
        image: "https://images.thdstatic.com/productImages/1106f884ec504424be799d9fe368a79f/svn/silver-jfvkaf-salt-pepper-mills-sa1129e227-64_600.jpg",
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
        image: "https://reactual.com/wp-content/uploads/2021/10/warmest-throw-blankets.jpg",
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
        image: "https://lampsdepot.com/cdn/shop/files/Anglepoise-Original-1227-Dove-Grey-Floor-Lamp.jpg?v=1685876300",
        shortDesc: "Elegant läslampa med riktbart huvud och fot i tung marmor.",
        longDesc: "Zenith är belysning när den är som mest skulptural. Den tunga marmorfoten ger stabilitet åt den slanka armen som kan vinklas exakt dit du behöver läsljus i läshörnan."
    },
    {
        id: 14,
        name: "Kust Handtvålpump i Stengods",
        category: "Inredning",
        price: 279,
        sku: "NV-INN-14",
        stock: 28,
        image: "https://1.bonami.cz/images/fit-crop-fill/9c/4b/9c4b3282570d5ff0288ac168e0e75f0e628ee7af-1000x1000.jpeg",
        shortDesc: "Tvålpump i glaserat stengods med rostfri pumpmekanism.",
        longDesc: "Lyft detaljerna i badrummet eller köket. Kust-serien i oglaserad stengods har en behaglig naturkänsla och står stabilt på handfatet utan att glida."
    },
    {
        id: 15,
        name: "Nova Smart Vägguttag med Energiövervakning",
        category: "Smart Hem",
        price: 249,
        sku: "NV-SMA-15",
        stock: 35,
        image: "https://mi-store.pl/hpeciai/b29755f3aa3db4c39a8276d52369c279/pol_pl_Gniazdko-Mi-Smart-Wi-Fi-Power-Plug-673_1.webp",
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
        image: "https://dowoodworks.se/cdn/shop/files/1744650863207.jpg?v=1744727222&width=1445",
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
        image: "https://videx.ua/files/products/52ccb6c3-f5eb-11f0-8512-78e7d1920002.1600x1340w.jpeg",
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
        image: "https://thepotlok.com/sys/uploads/2021/01/61qT2rUfWIL._AC_SL1500_.jpg",
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
        image: "https://www.taylorusa.com/cdn/shop/files/3817WH_TopDown.jpg?v=1746466739&width=700",
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
        image: "https://image.sofmap.com/images/product/pim/0810043376747_A02.jpg?v=20012001",
        shortDesc: "Kompakt luftrenare med True HEPA-13 filter och tyst nattläge.",
        longDesc: "Andas rent i sovrummet eller hemmakontoret. Nimbus fångar upp 99.97% av damm, pollen och fina partiklar. Utrustad med filterbyteindikator och diskret belysning."
    }
];

// Catalogue stays in preview mode until verified products are explicitly activated in Supabase.
let catalogueMode = 'preview';
const STORE_PREVIEW_ONLY = true; // Flip only after legal, supplier and operational launch gates are approved.

// Nordic Varda public catalogue API (publishable key only; never put service-role keys in browser code).
const SUPABASE_URL = 'https://oadjfqrfppckrtzbvlsv.supabase.co';
const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_UMpzaxkA21uV-MONB7gQ9Q_FgDtWm1_';

async function supabaseRequest(table, options = {}) {
    const response = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
        method: options.method || 'GET',
        headers: {
            'apikey': SUPABASE_PUBLISHABLE_KEY,
            'Authorization': `Bearer ${SUPABASE_PUBLISHABLE_KEY}`,
            'Content-Type': 'application/json',
            'Prefer': options.prefer || 'return=minimal'
        },
        body: options.body ? JSON.stringify(options.body) : undefined
    });
    if (!response.ok) {
        const detail = await response.text().catch(() => '');
        throw new Error(`Supabase ${table}: ${response.status} ${detail}`);
    }
    if (response.status === 204) return null;
    return response.json().catch(() => null);
}

async function loadPublishedProducts() {
    try {
        const response = await fetch(`${SUPABASE_URL}/rest/v1/products?select=id,slug,name,description,category,price_sek,image_url,sku,featured,inventory_status&active=eq.true&order=featured.desc,name.asc`, {
            headers: {
                'apikey': SUPABASE_PUBLISHABLE_KEY,
                'Authorization': `Bearer ${SUPABASE_PUBLISHABLE_KEY}`
            }
        });
        if (!response.ok) throw new Error(`Product API returned ${response.status}`);
        const rows = await response.json();
        if (Array.isArray(rows) && rows.length) {
            catalogueMode = 'live';
            products = rows.map((p, index) => ({
                id: p.id,
                name: p.name,
                category: p.category,
                price: p.price_sek,
                sku: p.sku || p.slug,
                stock: 0,
                image: p.image_url || '',
                shortDesc: (p.description || '').slice(0, 125),
                longDesc: p.description || '',
                featured: p.featured,
                inventoryStatus: p.inventory_status
            }));
            const liveIds = new Set(products.map(p => String(p.id)));
            cart = cart.filter(item => liveIds.has(String(item.id)));
            saveCart();
        } else {
            catalogueMode = 'preview';
            cart = [];
            saveCart();
        }
    } catch (error) {
        catalogueMode = 'preview';
        cart = [];
        saveCart();
        console.warn('Could not load live catalogue; using local preview catalogue.', error);
    }
}

// App State
let cart = [];
try {
    const storedCart = JSON.parse(localStorage.getItem('nordic_varda_cart') || '[]');
    cart = Array.isArray(storedCart) ? storedCart.filter(item => item && Number.isInteger(item.id) && Number.isFinite(item.price) && Number.isInteger(item.quantity) && item.quantity > 0) : [];
} catch (error) { cart = []; }
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
const cartOverlay = document.getElementById('cart-backdrop');
const closeCartBtn = document.getElementById('cart-close-btn');
const cartItemsContainer = document.getElementById('cart-items-container');
const cartBadge = document.getElementById('cart-badge');
const cartSubtotalEl = document.getElementById('cart-subtotal');
const cartShippingEl = document.getElementById('cart-shipping');
const cartTotalEl = document.getElementById('cart-total');
const freeShippingNotice = null;
const freeShippingProgress = null;
const checkoutBtn = document.getElementById('checkout-btn');

const productModal = document.getElementById('product-modal');
const modalOverlay = document.getElementById('modal-backdrop');
const closeModalBtn = document.getElementById('modal-close-btn');
const modalImage = document.getElementById('modal-img');
const modalCategory = document.getElementById('modal-category');
const modalTitle = document.getElementById('modal-title');
const modalPrice = document.getElementById('modal-price');
const modalSku = document.getElementById('modal-sku');
const modalStock = document.getElementById('modal-stock');
const modalDesc = document.getElementById('modal-desc');
const modalQtyInput = null;
const modalAddToCartBtn = document.getElementById('modal-add-btn');

const checkoutModal = document.getElementById('checkout-modal');
const checkoutOverlay = document.getElementById('checkout-backdrop');
const closeCheckoutBtn = document.getElementById('checkout-close-btn');
const checkoutForm = document.getElementById('checkout-form');
const checkoutSuccess = document.getElementById('checkout-success-msg');
const orderNumberEl = null;
const closeSuccessBtn = document.getElementById('checkout-reset-btn');

const cookieBanner = document.getElementById('cookie-banner');
const acceptCookiesBtn = document.getElementById('cookie-accept-btn');
const contactForm = document.getElementById('contact-form');
const newsletterForm = document.getElementById('newsletter-form');

// Initialize App
document.addEventListener('DOMContentLoaded', async () => {
    await loadPublishedProducts();
    renderProducts();
    updateCartUI();
    if (checkoutBtn && (STORE_PREVIEW_ONLY || catalogueMode !== 'live')) {
        checkoutBtn.disabled = true;
        checkoutBtn.textContent = 'Butiken förbereds';
        checkoutBtn.setAttribute('aria-label', 'Kassan öppnar när produkter och leverantörer har verifierats');
        checkoutBtn.classList.add('opacity-60', 'cursor-not-allowed');
    }
    setupEventListeners();
    if (STORE_PREVIEW_ONLY) {
        [contactForm, newsletterForm].forEach(form => {
            const submit = form?.querySelector('button[type="submit"]');
            if (submit) { submit.disabled = true; submit.textContent = 'Inte aktivt ännu'; submit.classList.add('opacity-60', 'cursor-not-allowed'); }
        });
    }
    checkCookies();

    // Handle the return from the hosted payment page.
    const checkoutState = new URLSearchParams(window.location.search).get('checkout');
    if (checkoutState === 'success') {
        cart = [];
        saveCart();
        updateCartUI();
        if (checkoutModal && checkoutForm && checkoutSuccess) {
            checkoutModal.classList.remove('hidden');
            checkoutForm.classList.add('hidden');
            checkoutSuccess.classList.remove('hidden');
            const message = checkoutSuccess.querySelector('p');
            const orderNumber = new URLSearchParams(window.location.search).get('order');
            if (message) message.textContent = orderNumber
                ? `Din betalning är genomförd. Ordernummer: ${orderNumber}.`
                : 'Din betalning är genomförd och ordern har registrerats.';
        }
        window.history.replaceState({}, document.title, window.location.pathname);
    } else if (checkoutState === 'cancelled') {
        window.history.replaceState({}, document.title, window.location.pathname);
    }
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
    if (cartToggleBtn && cartDrawer) {
        cartToggleBtn.addEventListener('click', openCart);
        closeCartBtn.addEventListener('click', closeCart);
        document.getElementById('cart-backdrop').addEventListener('click', closeCart);
    }

    // Modal close
    if (closeModalBtn && productModal) {
        closeModalBtn.addEventListener('click', closeModal);
        document.getElementById('modal-backdrop').addEventListener('click', closeModal);
    }

    // Checkout modal toggle
    if (checkoutBtn && checkoutModal) {
        checkoutBtn.addEventListener('click', () => {
            if (STORE_PREVIEW_ONLY || catalogueMode !== 'live') return;
            if (cart.length === 0) {
                alert('Din varukorg är tom.');
                return;
            }
            closeCart();
            openCheckout();
        });
        closeCheckoutBtn.addEventListener('click', closeCheckout);
        document.getElementById('checkout-backdrop').addEventListener('click', closeCheckout);
        document.getElementById('checkout-reset-btn').addEventListener('click', closeCheckout);
    }

    // Secure checkout: prices and product availability are always verified server-side.
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const button = checkoutForm.querySelector('button[type="submit"]');
            const errorEl = document.getElementById('checkout-error');
            const firstName = document.getElementById('checkout-first-name')?.value.trim();
            const lastName = document.getElementById('checkout-last-name')?.value.trim();
            const email = document.getElementById('checkout-email')?.value.trim();
            if (errorEl) { errorEl.textContent = ''; errorEl.classList.add('hidden'); }
            if (button) { button.disabled = true; button.textContent = 'Förbereder säker betalning...'; }

            try {
                const response = await fetch(`${SUPABASE_URL}/functions/v1/create-checkout-session`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'apikey': SUPABASE_PUBLISHABLE_KEY
                    },
                    body: JSON.stringify({
                        first_name: firstName,
                        last_name: lastName,
                        email,
                        items: cart.map(item => ({ product_id: String(item.id), quantity: item.quantity }))
                    })
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(data.error || 'Betalningen kunde inte startas.');
                if (!data.checkout_url) throw new Error('Betalningslänken saknas. Försök igen.');
                window.location.assign(data.checkout_url);
            } catch (error) {
                if (errorEl) {
                    errorEl.textContent = error.message || 'Ett fel uppstod. Försök igen senare.';
                    errorEl.classList.remove('hidden');
                }
            } finally {
                if (button) { button.disabled = false; button.textContent = 'Fortsätt till säker betalning'; }
            }
        });
    }

    // Cookie consent
    if (acceptCookiesBtn && cookieBanner) {
        acceptCookiesBtn.addEventListener('click', () => {
            localStorage.setItem('nordic_varda_cookies', 'accepted');
            cookieBanner.classList.add('hidden');
        });
    }

    // Contact form: save messages in the isolated Nordic Varda database.
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const button = contactForm.querySelector('button[type="submit"]');
            const success = document.getElementById('contact-success');
            const name = document.getElementById('contact-name')?.value.trim();
            const email = document.getElementById('contact-email')?.value.trim();
            const message = document.getElementById('contact-message')?.value.trim();
            if (button) { button.disabled = true; button.textContent = 'Skickar...'; }
            try {
                await supabaseRequest('contact_messages', { method: 'POST', body: { name, email, message } });
                if (success) { success.textContent = 'Tack! Ditt meddelande har skickats.'; success.classList.remove('hidden'); }
                contactForm.reset();
            } catch (error) {
                console.error(error);
                if (success) { success.textContent = 'Meddelandet kunde inte skickas just nu. Försök igen senare.'; success.classList.remove('hidden'); }
            } finally {
                if (button) { button.disabled = false; button.textContent = 'Skicka meddelande'; }
            }
        });
    }

    // Newsletter: store consent-backed subscriptions in the isolated database.
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const button = newsletterForm.querySelector('button[type="submit"]');
            const success = document.getElementById('newsletter-success');
            const email = document.getElementById('newsletter-email')?.value.trim();
            if (button) { button.disabled = true; button.textContent = 'Registrerar...'; }
            try {
                await supabaseRequest('newsletter_subscribers', { method: 'POST', body: { email, consent_text_version: 'v1' } });
                if (success) { success.textContent = 'Tack! Du är nu registrerad för nyhetsbrevet.'; success.classList.remove('hidden'); }
                newsletterForm.reset();
            } catch (error) {
                console.error(error);
                if (success) { success.textContent = 'Kunde inte registrera e-postadressen. Kontrollera den eller försök igen senare.'; success.classList.remove('hidden'); }
            } finally {
                if (button) { button.disabled = false; button.textContent = 'Prenumerera'; }
            }
        });
    }

    // Modal Add To Cart
    if (modalAddToCartBtn) {
        modalAddToCartBtn.addEventListener('click', () => {
            if (!activeModalProduct) return;
            const qty = 1;
            addToCart(activeModalProduct.id, qty);
            closeModal();
            openCart();
        });
    }
}

function checkCookies() {
    try {
        if (localStorage.getItem('nordic_varda_cookies') === 'accepted') {
            if (cookieBanner) cookieBanner.classList.add('hidden');
        } else if (cookieBanner) {
            cookieBanner.classList.remove('hidden');
        }
    } catch (error) {
        if (cookieBanner) cookieBanner.classList.remove('hidden');
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
    } else if (currentSort === 'name' || currentSort === 'name-asc') {
        result.sort((a, b) => a.name.localeCompare(b.name, 'sv'));
    }

    return result;
}

function renderProducts() {
    if (!productGrid) return;
    const filtered = getFilteredAndSortedProducts();
    if (productCountEl) productCountEl.textContent = `${filtered.length} st produkter`;

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
                    <img src="${product.image}" alt="${product.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22600%22%3E%3Crect width=%22800%22 height=%22600%22 fill=%22%23eee9e1%22/%3E%3C/svg%3E'">
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
    modalImage.onerror = () => { modalImage.onerror = null; modalImage.src = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22600%22%3E%3Crect width=%22800%22 height=%22600%22 fill=%22%23eee9e1%22/%3E%3C/svg%3E'; };
    modalCategory.textContent = product.category;
    modalTitle.textContent = product.name;
    modalPrice.textContent = `${product.price} SEK`;
    modalSku.textContent = product.sku;
    modalStock.textContent = `${product.stock} st i lager`;
    modalDesc.textContent = product.longDesc;
    

    productModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    if (productModal) productModal.classList.add('hidden');
    document.body.style.overflow = '';
    activeModalProduct = null;
}

// Cart Functions
function openCart() {
    if (!cartDrawer) return;
    cartDrawer.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeCart() {
    if (!cartDrawer) return;
    cartDrawer.classList.add('hidden');
    document.body.style.overflow = '';
}

function addToCart(productId, quantity = 1) {
    if (STORE_PREVIEW_ONLY || catalogueMode !== 'live') {
        alert('Det här är en förhandsvisning. Köp öppnar när produkter, leverantörer och butikens villkor har verifierats.');
        return;
    }
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
    try { localStorage.setItem('nordic_varda_cart', JSON.stringify(cart)); }
    catch (error) { console.warn('Varukorgen kunde inte sparas lokalt.', error); }
}

function updateCartUI() {
    const totalCount = cart.reduce((sum, item) => sum + item.quantity, 0);
    if (cartBadge) cartBadge.textContent = totalCount;

    if (cart.length === 0) {
        if (cartItemsContainer) cartItemsContainer.innerHTML = `
            <div class="py-12 text-center text-[#5A5E63]">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12  mx-auto mb-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                <p>Din varukorg är tom.</p>
            </div>
        `;
        if (cartSubtotalEl) cartSubtotalEl.textContent = '0 SEK';
        if (cartShippingEl) cartShippingEl.textContent = '0 SEK';
        if (cartTotalEl) cartTotalEl.textContent = '0 SEK';
        if (freeShippingNotice) freeShippingNotice.innerHTML = `Lägg till produkter för <span class="font-bold">500 SEK</span> till för fri frakt!`;
        if (freeShippingProgress) freeShippingProgress.style.width = '0%';
        return;
    }

    if (cartItemsContainer) cartItemsContainer.innerHTML = cart.map(item => `
        <div class="flex items-center space-x-4 py-4 border-b border-[#EAE5DE]">
            <img src="${item.image}" alt="${item.name}" class="w-16 h-16 object-cover rounded-xl bg-[#EAE5DE]" onerror="this.onerror=null;this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22800%22 height=%22600%22%3E%3Crect width=%22800%22 height=%22600%22 fill=%22%23eee9e1%22/%3E%3C/svg%3E'">
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

    if (cartSubtotalEl) cartSubtotalEl.textContent = `${subtotal} SEK`;
    if (cartShippingEl) cartShippingEl.textContent = shipping === 0 ? 'Fri frakt' : `${shipping} SEK`;
    if (cartTotalEl) cartTotalEl.textContent = `${total} SEK`;

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
    if (checkoutModal) checkoutModal.classList.add('hidden');
    document.body.style.overflow = '';
}