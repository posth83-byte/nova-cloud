(() => {
  "use strict";
  const products = [
    {id:"lamp",name:"Nordic bordslampa",category:"belysning",categoryLabel:"Belysning",price:799,badge:"Utvald",description:"En mjuk och tidlös form som ger ett varmt ljus till hemmets lugna hörn.",image:"https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=900&q=85",alt:"Modern bordslampa i varm inredningsmiljö"},
    {id:"throw",name:"Mjuk ullpläd",category:"textil",categoryLabel:"Textil",price:649,badge:"",description:"En ombonad detalj för soffan, fåtöljen eller sängen.",image:"https://images.unsplash.com/photo-1600369671236-e74521d4b6ad?auto=format&fit=crop&w=900&q=85",alt:"Varmt textilmaterial och pläd"},
    {id:"mug",name:"Keramikmugg Kust",category:"dukning",categoryLabel:"Dukning",price:229,badge:"",description:"En enkel kopp med hantverkskänsla för dagens första kaffe.",image:"https://images.unsplash.com/photo-1514228742587-6b1558f 즉".replace(" ", ""),alt:"Keramikkopp på ett bord"},
    {id:"candle",name:"Doftljus Stillhet",category:"inredning",categoryLabel:"Inredning",price:279,badge:"",description:"Skapa en varm och rofylld känsla med en diskret inredningsdetalj.",image:"https://images.unsplash.com/photo-1603006905003-be475563bc59?auto=format&fit=crop&w=900&q=85",alt:"Tända doftljus i lugn miljö"},
    {id:"table",name:"Sidobord Form",category:"inredning",categoryLabel:"Inredning",price:1499,badge:"",description:"Ett nätt sidobord som passar bredvid soffan eller sängen.",image:"https://images.unsplash.com/photo-1499933374294-4584851497cc?auto=format&fit=crop&w=900&q=85",alt:"Stilrent bord i ljust rum"},
    {id:"linen",name:"Linneservetter 4-pack",category:"textil",categoryLabel:"Textil",price:349,badge:"",description:"Naturlig struktur som gör både vardag och helgdukning finare.",image:"https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=900&q=85",alt:"Naturlig dukning och textilier"}
  ];
  const $ = (selector, root=document) => root.querySelector(selector);
  const $$ = (selector, root=document) => Array.from(root.querySelectorAll(selector));
  const money = value => new Intl.NumberFormat("sv-SE").format(value) + " kr";
  let cart = [];
  try { const stored = JSON.parse(localStorage.getItem("nexora-cart") || "[]"); if (Array.isArray(stored)) cart = stored.filter(line => products.some(p => p.id === line.id) && Number.isInteger(line.quantity) && line.quantity > 0); } catch (_) { cart = []; }
  let category = "alla";
  let search = "";

  function saveCart(){ try { localStorage.setItem("nexora-cart", JSON.stringify(cart)); } catch (_) {} }
  function visibleProducts(){ return products.filter(p => (category === "alla" || p.category === category) && (p.name + " " + p.description + " " + p.categoryLabel).toLocaleLowerCase("sv").includes(search)); }
  function renderProducts(){
    const grid=$("#productGrid"); if(!grid) return;
    const matches=visibleProducts();
    $("#resultCount").textContent=matches.length+" produkter";
    if(!matches.length){grid.innerHTML='<p class="empty-state">Vi hittade inga produkter. Prova ett annat sökord.</p>';return;}
    grid.innerHTML=matches.map(p=>'<article class="product-card" data-product="'+p.id+'"><div class="product-image-wrap"><img class="product-image" src="'+p.image+'" alt="'+p.alt+'" loading="lazy"><span class="product-badge">'+(p.badge||p.categoryLabel)+'</span><button class="quick-add" type="button" data-add="'+p.id+'">Lägg i varukorg</button></div><div class="product-info"><span class="product-category">'+p.categoryLabel+'</span><div class="product-title-row"><h3 class="product-title">'+p.name+'</h3><span class="product-price">'+money(p.price)+'</span></div><p class="product-description">'+p.description+'</p></div></article>').join("");
  }
  function cartCount(){return cart.reduce((sum,line)=>sum+line.quantity,0);}
  function cartTotal(){return cart.reduce((sum,line)=>{const p=products.find(item=>item.id===line.id);return sum+(p?p.price*line.quantity:0);},0);}
  function renderCart(){
    const count=cartCount(), total=cartTotal();
    $("#cartCount").textContent=count; $("#drawerCount").textContent="("+count+")"; $("#cartSubtotal").textContent=money(total); $("#checkoutTotal").textContent=money(total);
    const lines=$("#cartLines");
    if(!cart.length){lines.innerHTML='<p class="empty-cart">Din varukorg är tom.<br>Hitta något du tycker om i kollektionen.</p>';return;}
    lines.innerHTML=cart.map(line=>{const p=products.find(item=>item.id===line.id);return '<div class="cart-line" data-line="'+p.id+'"><img src="'+p.image+'" alt=""><div><h3>'+p.name+'</h3><p>'+money(p.price)+'</p><div class="quantity-control"><button type="button" data-quantity="-1" data-id="'+p.id+'" aria-label="Minska antal">−</button><span>'+line.quantity+'</span><button type="button" data-quantity="1" data-id="'+p.id+'" aria-label="Öka antal">+</button></div></div><button class="remove-line" type="button" data-remove="'+p.id+'">Ta bort</button></div>';}).join("");
  }
  function addToCart(id){const line=cart.find(item=>item.id===id);if(line)line.quantity+=1;else cart.push({id,quantity:1});saveCart();renderCart();showToast("Produkten har lagts i varukorgen.");}
  function openCart(){renderCart();$("#cartDrawer").classList.add("open");$("#drawerBackdrop").classList.add("open");$("#cartDrawer").setAttribute("aria-hidden","false");document.body.style.overflow="hidden";}
  function closeCart(){ $("#cartDrawer").classList.remove("open");$("#drawerBackdrop").classList.remove("open");$("#cartDrawer").setAttribute("aria-hidden","true");document.body.style.overflow="";}
  function openCheckout(){if(!cart.length){showToast("Varukorgen är tom.");return;}closeCart();$("#checkoutBackdrop").classList.add("open");$("#checkoutSuccess").hidden=true;$("#checkoutForm").hidden=false;document.body.style.overflow="hidden";}
  function closeCheckout(){ $("#checkoutBackdrop").classList.remove("open");document.body.style.overflow="";}
  let toastTimer;
  function showToast(message){const toast=$("#toast");toast.textContent=message;toast.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove("show"),2200);}
  $("#productGrid").addEventListener("click",event=>{const button=event.target.closest("[data-add]");if(button)addToCart(button.dataset.add);});
  $("#filterRow").addEventListener("click",event=>{const button=event.target.closest("[data-category]");if(!button)return;category=button.dataset.category;$$(".filter-chip").forEach(chip=>chip.classList.toggle("active",chip===button));renderProducts();});
  $("#searchInput").addEventListener("input",event=>{search=event.target.value.trim().toLocaleLowerCase("sv");renderProducts();});
  $("#cartOpen").addEventListener("click",openCart);$("#cartClose").addEventListener("click",closeCart);$("#drawerBackdrop").addEventListener("click",closeCart);
  $("#cartLines").addEventListener("click",event=>{const qty=event.target.closest("[data-quantity]");const remove=event.target.closest("[data-remove]");if(qty){const line=cart.find(item=>item.id===qty.dataset.id);if(line){line.quantity+=Number(qty.dataset.quantity);if(line.quantity<1)cart=cart.filter(item=>item.id!==qty.dataset.id);}}else if(remove){cart=cart.filter(item=>item.id!==remove.dataset.remove);}saveCart();renderCart();});
  $("#checkoutOpen").addEventListener("click",openCheckout);$("#checkoutClose").addEventListener("click",closeCheckout);
  $("#checkoutBackdrop").addEventListener("click",event=>{if(event.target===$("#checkoutBackdrop"))closeCheckout();});
  $("#checkoutForm").addEventListener("submit",event=>{event.preventDefault();if(!cart.length)return;const order="NX-TEST-"+Math.floor(100000+Math.random()*900000);$("#successOrderNumber").textContent="Referensnummer: "+order;$("#checkoutForm").hidden=true;$("#checkoutSuccess").hidden=false;cart=[];saveCart();renderCart();});
  $("#continueShopping").addEventListener("click",()=>{closeCheckout();showToast("Tack för att du testade NEXORA.");});
  $("#explore-btn")?.addEventListener("click",()=>$("#produkter").scrollIntoView({behavior:"smooth"}));
  $("#newsletterForm").addEventListener("submit",event=>{event.preventDefault();$("#newsletterMessage").textContent="Tack! Detta är en visningsfunktion och ingen prenumeration har sparats.";event.target.reset();});
  $("#currentYear").textContent=new Date().getFullYear();
  renderProducts();renderCart();
})();