"""Free procedural short-video engine for JARVIS Video Team.

Creates original 9:16 videos locally with Pillow, FFmpeg and Swedish Edge TTS.
No paid generative-video API is used. Visuals are animated procedural scenes,
not photorealistic text-to-video generation.
"""
import asyncio
import html
import math
import re
import shutil
import subprocess
import uuid
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse
from video_assets import search_commons_images, download_commons_image
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

router = APIRouter()
OUTPUT_DIR = Path("/tmp/nova_team_created")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VOICE = "sv-SE-MattiasNeural"
W, H, FPS = 720, 1280, 25
MAX_PROMPT = 220
SCENE_SECONDS = 5.2


def _ffmpeg(args, timeout=600):
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout
    )
    if result.returncode:
        raise RuntimeError((result.stderr or "FFmpeg misslyckades.")[-1600:])


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _centered(draw, text, y, font, fill, max_width=590, gap=12):
    lines = _wrap(draw, text, font, max_width)[:4]
    height = len(lines) * (font.size + gap)
    top = y - height / 2
    for line in lines:
        draw.text((W // 2, int(top)), line, font=font, fill=fill, anchor="ma",
                  stroke_width=2, stroke_fill=(4, 9, 20))
        top += font.size + gap


def _draw_illustration(draw, kind, t):
    """Draw a distinct vector illustration for each scene template."""
    cx, cy = W // 2, 410
    glow = int(20 + 12 * (0.5 + 0.5 * math.sin(t * 2.2)))
    orange = (255, 145 + glow, 83)
    pale = (225, 237, 255)
    if kind == "coffee":
        draw.rounded_rectangle((245, 300, 465, 515), radius=38,
                               fill=(40, 65, 91), outline=orange, width=8)
        draw.arc((425, 340, 535, 470), 270, 90, fill=orange, width=13)
        draw.line((270, 280, 300, 225), fill=pale, width=8)
        draw.line((355, 280, 355, 210), fill=pale, width=8)
        draw.line((440, 280, 410, 225), fill=pale, width=8)
        draw.ellipse((280, 325, 430, 390), fill=(122, 77, 53), outline=orange, width=4)
    elif kind == "sleep":
        draw.ellipse((190, 270, 530, 610), fill=(29, 48, 83), outline=(142, 173, 239), width=7)
        draw.ellipse((275, 235, 555, 535), fill=(7, 13, 29))
        for x, y, r in [(170, 280, 8), (520, 240, 7), (550, 540, 6), (175, 560, 5)]:
            draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 206, 143))
        draw.text((cx, 635), "Z z z", font=_font(54, True), fill=pale, anchor="mm")
    elif kind == "phone":
        draw.rounded_rectangle((260, 210, 460, 620), radius=35,
                               fill=(16, 24, 43), outline=orange, width=9)
        draw.rounded_rectangle((280, 250, 440, 555), radius=18, fill=(39, 58, 91))
        draw.ellipse((330, 350, 390, 410), fill=orange)
        draw.rounded_rectangle((305, 445, 415, 465), radius=10, fill=pale)
        draw.rounded_rectangle((320, 480, 400, 495), radius=8, fill=(150, 177, 215))
    elif kind == "work":
        draw.rounded_rectangle((150, 300, 570, 540), radius=22,
                               fill=(22, 37, 61), outline=(105, 187, 229), width=7)
        draw.rectangle((185, 335, 535, 490), fill=(11, 22, 42))
        for i in range(4):
            y = 365 + i * 30
            draw.rounded_rectangle((215, y, 430 + (i % 2) * 45, y+10), radius=5, fill=orange if i == 2 else pale)
        draw.line((360, 540, 360, 605), fill=pale, width=12)
        draw.line((275, 610, 445, 610), fill=pale, width=12)
    elif kind == "money":
        draw.ellipse((205, 245, 515, 555), fill=(34, 75, 66), outline=(133, 224, 169), width=9)
        draw.text((360, 400), "kr", font=_font(115, True), fill=(190, 255, 211), anchor="mm")
        for x, y in [(170, 310), (540, 300), (185, 540), (525, 550)]:
            draw.text((x, y), "?", font=_font(52, True), fill=orange, anchor="mm")
    elif kind == "gym":
        draw.rounded_rectangle((305, 275, 415, 560), radius=45, fill=(44, 65, 91), outline=orange, width=8)
        draw.ellipse((260, 245, 460, 445), fill=(44, 65, 91), outline=pale, width=7)
        draw.line((180, 390, 540, 390), fill=orange, width=18)
        for x in (190, 510):
            draw.rounded_rectangle((x-28, 320, x+28, 460), radius=14, fill=(104, 135, 177), outline=pale, width=5)
        draw.text((360, 640), "1 REP", font=_font(48, True), fill=orange, anchor="mm")
    elif kind == "food":
        draw.ellipse((185, 280, 535, 630), fill=(225, 232, 239), outline=orange, width=12)
        draw.ellipse((230, 325, 490, 585), fill=(63, 105, 74), outline=(255, 255, 255), width=5)
        for x, y in ((300, 390), (420, 450), (350, 520), (440, 360)):
            draw.ellipse((x-34, y-34, x+34, y+34), fill=(231, 112, 81), outline=(255, 221, 174), width=4)
        draw.arc((270, 215, 450, 390), 190, 350, fill=pale, width=9)
    elif kind == "love":
        draw.ellipse((190, 275, 530, 615), fill=(63, 38, 70), outline=(255, 139, 177), width=8)
        draw.text((360, 430), "♥", font=_font(180, True), fill=(255, 111, 159), anchor="mm")
        draw.text((205, 270), "…", font=_font(65, True), fill=pale, anchor="mm")
        draw.text((515, 585), "?", font=_font(70, True), fill=orange, anchor="mm")
    else:
        # A cinematic spotlight and abstract character silhouette.
        draw.ellipse((220, 245, 500, 525), fill=(39, 62, 94), outline=orange, width=8)
        draw.ellipse((305, 305, 415, 415), fill=(190, 208, 236))
        draw.rounded_rectangle((270, 420, 450, 620), radius=80, fill=(104, 132, 174))
        draw.arc((150, 170, 570, 690), 205, 335, fill=(83, 180, 224), width=5)


def _make_scene(path, kicker, headline, caption, kind, index, background_path=None):
    if background_path and Path(background_path).is_file():
        with Image.open(background_path) as source:
            image = ImageOps.fit(source.convert("RGB"), (W, H), method=Image.Resampling.LANCZOS)
        image = ImageEnhance.Brightness(image).enhance(0.34)
        shade = Image.new("RGBA", (W, H), (4, 9, 20, 112))
        image = Image.alpha_composite(image.convert("RGBA"), shade).convert("RGB")
    else:
        image = Image.new("RGB", (W, H), (5, 10, 22))
        pixels = image.load()
        for y in range(H):
            f = y / H
            base = (int(6 + 12*f), int(12 + 12*f), int(28 + 16*f))
            for x in range(W):
                glow = max(0.0, 1 - (((x-W*.5)/(W*.78))**2 + ((y-H*.34)/(H*.62))**2))
                pixels[x, y] = (min(255, base[0] + int(20*glow)),
                                min(255, base[1] + int(29*glow)),
                                min(255, base[2] + int(42*glow)))
    draw = ImageDraw.Draw(image)
    palettes = {
        "coffee": (255, 151, 91), "sleep": (142, 173, 239), "phone": (105, 187, 229),
        "work": (105, 187, 229), "money": (133, 224, 169), "gym": (255, 145, 83),
        "food": (255, 181, 115), "love": (255, 139, 177),
    }
    accent = palettes.get(kind, (255, 151, 91))
    draw.rounded_rectangle((34, 42, W-34, H-42), radius=34,
                           outline=(80, 119, 167), width=2)
    # Scene-specific ambient marks create a distinct visual identity for each beat.
    if kind == "sleep":
        for sx, sy, radius in ((95, 245, 4), (590, 285, 5), (115, 710, 3), (575, 690, 4)):
            draw.ellipse((sx-radius, sy-radius, sx+radius, sy+radius), fill=(210, 222, 255))
    elif kind in ("coffee", "food"):
        for sx in (110, 610):
            draw.arc((sx-35, 260, sx+35, 390), 190, 330, fill=accent, width=4)
    elif kind == "work":
        for sy in range(230, 690, 70):
            draw.line((82, sy, 638, sy), fill=(22, 38, 59), width=1)
    elif kind == "love":
        draw.arc((100, 220, 620, 740), 195, 345, fill=accent, width=5)
    elif kind == "gym":
        for sx in (110, 610):
            draw.line((sx, 260, sx, 700), fill=(70, 48, 73), width=5)
    draw.text((62, 75), "JARVIS ORIGINALS", font=_font(22, True), fill=(153, 184, 220))
    draw.rounded_rectangle((58, 120, W-58, 178), radius=20,
                           fill=(20, 39, 61), outline=(255, 151, 91), width=2)
    draw.text((W//2, 149), kicker.upper(), font=_font(25, True),
              fill=(255, 190, 145), anchor="mm")
    _draw_illustration(draw, kind, index * SCENE_SECONDS)
    _centered(draw, headline, 765, _font(49 if len(headline) < 36 else 42, True),
              (248, 250, 255), max_width=600, gap=14)
    # High-contrast subtitle panel for sound-off viewing.
    draw.rounded_rectangle((58, 910, W-58, 1080), radius=22,
                           fill=(3, 8, 18), outline=(255, 151, 91), width=2)
    _centered(draw, caption, 995, _font(31, True), (255, 232, 213), max_width=555, gap=9)
    draw.text((W//2, 1165), f"{index+1:02d} / 05     •     JARVIS VIDEO TEAM",
              font=_font(18, True), fill=(153, 178, 211), anchor="mm")
    image.save(path, quality=94)


def _build_script(topic, video_type="humor"):
    clean = re.sub(r"\s+", " ", (topic or "").strip())[:MAX_PROMPT].strip(" .!?")
    if not clean:
        clean = "vardagslivet"
    templates = {
        "explainer": [
            ("FRÅGAN", f"Vad behöver man förstå om {clean}?", "Vi börjar med grunden och håller det enkelt.", "generic"),
            ("BAKGRUNDEN", f"För att förstå {clean} behöver vi se sammanhanget.", "Det blir lättare när man delar upp det.", "work"),
            ("KÄRNAN", f"Den viktigaste delen av {clean} är det vi ska fokusera på.", "En tydlig sak i taget gör skillnad.", "phone"),
            ("EXEMPEL", f"Tänk på ett konkret exempel kopplat till {clean}.", "Då blir resonemanget lättare att följa.", "generic"),
            ("SAMMANFATTNING", f"Nu har du en tydligare bild av {clean}.", "Kontrollera detaljerna innan du drar slutsatser.", "generic"),
        ],
        "tutorial": [
            ("MÅLET", f"Så kommer du igång med {clean}.", "Vi tar det steg för steg.", "generic"),
            ("STEG 1", "Börja med att förbereda det du behöver.", "En bra start gör resten enklare.", "work"),
            ("STEG 2", f"Gå igenom grunderna för {clean} i lugn takt.", "Följ instruktionerna för just din situation.", "phone"),
            ("STEG 3", "Testa resultatet och rätta till det som inte fungerar.", "Små justeringar är helt normala.", "generic"),
            ("KLART", "Nu har du en tydlig startpunkt.", "Kontrollera alltid resultatet innan du går vidare.", "generic"),
        ],
        "promo": [
            ("UPPTÄCK", f"Letar du efter ett bättre sätt att ta dig an {clean}?", "Här är en idé värd att utforska.", "generic"),
            ("UTMANINGEN", f"{clean.capitalize()} kan kännas mer komplicerat än det behöver vara.", "Det ska vara enkelt att komma igång.", "work"),
            ("MÖJLIGHETEN", "Fokusera på det som faktiskt gör skillnad.", "Tydlighet och enkelhet först.", "phone"),
            ("FÖRDELEN", "Jämför alternativen och välj det som passar dina behov.", "Inga tomma löften – välj det som fungerar.", "money"),
            ("TA NÄSTA STEG", f"Utforska {clean} och se vad som passar dig.", "Läs mer innan du bestämmer dig.", "generic"),
        ],
        "inspiration": [
            ("BÖRJA", f"Du behöver inte ha allt klart för att börja med {clean}.", "Det räcker att ta första steget.", "generic"),
            ("SMÅ STEG", "Framsteg byggs av små beslut som upprepas.", "Hellre lite i taget än aldrig.", "work"),
            ("MOTGÅNG", "Det kommer inte alltid gå enligt planen.", "Det betyder inte att du ska ge upp.", "sleep"),
            ("UTVECKLING", f"Varje försök lär dig något om {clean}.", "Använd erfarenheten och fortsätt framåt.", "phone"),
            ("FORTSÄTT", "Ditt nästa steg behöver inte vara perfekt.", "Det behöver bara bli av.", "generic"),
        ],
        "story": [
            ("DET BÖRJADE", f"Allt började med en enkel idé: {clean}.", "Ingen visste vart det skulle leda.", "generic"),
            ("FÖRSTA STEGET", "Till en början verkade allt ganska enkelt.", "Sedan dök den första överraskningen upp.", "work"),
            ("VÄNDPUNKTEN", "Plötsligt behövde en helt ny plan ta form.", "Det var nu berättelsen tog fart.", "phone"),
            ("UPPTÄCKTEN", "Det som först verkade vara ett hinder blev en möjlighet.", "Ibland ser man lösningen först efteråt.", "generic"),
            ("SLUTET", f"Det här var början på berättelsen om {clean}.", "Resten kan du själv vara med och forma.", "generic"),
        ],
    }
    if video_type in templates:
        return templates[video_type]
    lower = clean.casefold()
    if any(word in lower for word in ("kaffe", "kaffet", "espresso")):
        beats = [
            ("DAGENS PLAN", "Jag skulle bara ta en snabb kaffe.", "Det var innan kaffemaskinen fick en egen åsikt.", "coffee"),
            ("FÖRSTA FÖRSÖKET", "Tryckte på start. Ingenting hände.", "Maskinen behövde tydligen också måndag morgon.", "coffee"),
            ("STRATEGIN", "Jag googlade: hur lagar man en kaffemaskin?", "Internet föreslog att jag skulle andas lugnt.", "phone"),
            ("INSIKTEN", "Jag hade nu lagt 20 minuter på kaffe.", "Produktiviteten låg fortfarande på 0 procent.", "work"),
            ("SLUTSATSEN", "Så jag tog en kopp te istället.", "Nu är jag stressad OCH besviken.", "coffee"),
        ]
    elif any(word in lower for word in ("sova", "sömn", "natt", "hjärnan")):
        beats = [
            ("02:47", "Du ska bara sova.", "Äntligen lite lugn och ro.", "sleep"),
            ("HJÄRNAN", "Kommer du ihåg det pinsamma från 2016?", "Det där som ingen annan minns längre.", "sleep"),
            ("DU", "Nej. Och det tänker jag inte göra heller.", "Vi har faktiskt ett schema här.", "phone"),
            ("HJÄRNAN", "Perfekt. Här är det i 4K med surroundljud.", "Bonus: du sa det med självförtroende.", "phone"),
            ("03:19", "Ska vi gå igenom RESTEN av ditt liv också?", "Sov gott. Om 4–5 arbetsdagar.", "sleep"),
        ]
    elif any(word in lower for word in ("jobb", "chef", "möte", "måndag", "arbete")):
        beats = [
            ("MÅNDAG 08:00", "Den här veckan ska jag vara effektiv.", "Jag har till och med gjort en lista.", "work"),
            ("08:07", "Första mötet börjar om tre minuter.", "Ingen vet varför jag är med.", "phone"),
            ("09:42", "Någon säger: vi tar det offline.", "Jag har varit online hela mitt liv.", "work"),
            ("14:56", "Jag har svarat på 38 mejl.", "Och gjort exakt noll av jobbet.", "work"),
            ("17:01", "Imorgon kör vi på riktigt.", "Det sa jag även förra måndagen.", "sleep"),
        ]
    elif any(word in lower for word in ("gym", "träna", "träning", "motion")):
        beats = [
            ("MÅLET", "Idag börjar mitt nya träningsliv.", "Jag har till och med köpt vattenflaska.", "gym"),
            ("UPPVÄRMNING", "Jag googlade hur man värmer upp.", "Blev trött av att läsa instruktionerna.", "phone"),
            ("FÖRSTA SETET", "Jag lyfte en hantel. En gång.", "Musklerna har redan skickat klagomål.", "gym"),
            ("ÅTERHÄMTNING", "Jag vilade i 47 minuter.", "Det kallas tydligen aktiv återhämtning.", "sleep"),
            ("RESULTATET", "Jag har tränat hela dagen.", "Stegräknaren visar 312 steg. Mest till fiket.", "coffee"),
        ]
    elif any(word in lower for word in ("pengar", "lön", "budget", "faktura", "ekonomi")):
        beats = [
            ("LÖNEDAG", "Lönen kom precis in på kontot.", "Jag kände mig ekonomiskt odödlig.", "money"),
            ("FÖRSTA TIMMEN", "Jag köpte bara det allra nödvändigaste.", "En kaffemaskin och en liten båt.", "coffee"),
            ("VERKLIGHETEN", "Hyran och räkningarna vaknade.", "De hade tydligen planerat en överraskning.", "phone"),
            ("BUDGETMÖTET", "Jag öppnade min budget med stort mod.", "Budgeten öppnade istället ett krisärende.", "work"),
            ("SLUTET", "Nu lever jag på nudlar till nästa lön.", "Men båten var faktiskt värd det.", "food"),
        ]
    elif any(word in lower for word in ("dejt", "relation", "kärlek", "partner")):
        beats = [
            ("INFÖR DEJTEN", "Jag skulle vara avslappnad och naturlig.", "Övade på att säga hej i spegeln.", "love"),
            ("FÖRSTA INTRYCKET", "Jag sa: trevligt att träffas.", "Och råkade kalla personen för mamma.", "love"),
            ("SMÅPRAT", "Vi pratade om vädret i tjugo minuter.", "Meteorologin gick bättre än romantiken.", "phone"),
            ("TYSTNADEN", "Jag skulle säga något charmigt.", "Hjärnan visade bara laddningssymbolen.", "generic"),
            ("EFTERÅT", "De sa att vi hörs snart.", "Jag har redan planerat bröllopet. Och flytten.", "love"),
        ]
    elif any(word in lower for word in ("mat", "middag", "laga", "recept", "matlagning")):
        beats = [
            ("MIDDAGSPLANEN", "Ikväll lagar jag något avancerat.", "Jag har sparat ett recept från internet.", "food"),
            ("INGREDIENSERNA", "Det saknas bara en liten ingrediens.", "Och tydligen resten av köket.", "food"),
            ("KOCKEN", "Jag improviserar lite istället.", "Brandvarnaren blir min souschef.", "work"),
            ("PROBLEMET", "Receptet sa: stek tills gyllenbrunt.", "Min panna gick direkt till kolsvart.", "food"),
            ("SERVERING", "Det blev mackor till middag igen.", "Michelin får vänta tills imorgon.", "food"),
        ]
    else:
        beats = [
            ("JAG HADE EN PLAN", f"Idag skulle jag äntligen lyckas med {clean}.", "Hur svårt kunde det vara?", "generic"),
            ("SJÄLVFÖRTROENDE", "Jag hade sett en video på 12 sekunder.", "Nu räknade jag mig som expert.", "phone"),
            ("VERKLIGHETEN", "Tre sekunder senare gick allt åt fel håll.", "Självförtroendet var kvar. Kompetensen tog ledigt.", "work"),
            ("FELSÖKNING", "Jag testade exakt samma sak igen.", "För tydligen fungerar envishet som teknik.", "generic"),
            ("LÄRDOMEN", f"Nästa gång ska jag läsa på om {clean}.", "Eller låta bli. Vi får se.", "generic"),
        ]
    return beats


def _motion_filter(kind, index, video_type="humor"):
    """Build a lightweight animated FFmpeg filter for floating comic accents."""
    palettes = {
        "coffee": "0xFF975B", "sleep": "0xAFC5FF", "phone": "0x69BBE5",
        "work": "0x69BBE5", "money": "0x85E0A9", "gym": "0xFF9153",
        "food": "0xFFB573", "love": "0xFF8BB1", "generic": "0xFF975B",
    }
    color = palettes.get(kind, "0xFF975B")
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    phase = index * 0.73
    frames = int(SCENE_SECONDS * FPS)
    # A final, timed reaction word gives every scene a readable comic button.
    reactions = {
        "coffee": "SLURP!", "sleep": "ZZZ!", "phone": "PING!",
        "work": "OJ!", "money": "KRASCH!", "gym": "PUH!",
        "food": "MUMS!", "love": "OJ DA!", "generic": "PANG!",
    }
    reaction = reactions.get(kind, "PANG!") if video_type == "humor" else ""
    return ",".join([
        f"scale={W}:{H}",
        f"zoompan=z='1.025+0.012*sin(on/22)':"
        f"x='iw/2-(iw/zoom/2)+7*sin(on/19)':"
        f"y='ih/2-(ih/zoom/2)+10*cos(on/27)':d={frames}:s={W}x{H}:fps={FPS}",
        f"drawtext=fontfile={font}:text='*':fontcolor={color}:fontsize=42:"
        f"x='92+24*sin(t*2.4+{phase:.2f})':y='300+32*cos(t*2.0+{phase:.2f})'",
        f"drawtext=fontfile={font}:text='+':fontcolor={color}:fontsize=34:"
        f"x='560+28*cos(t*1.9+{phase:.2f})':y='520+25*sin(t*2.7+{phase:.2f})'",
        f"drawtext=fontfile={font}:text='{reaction}':fontcolor={color}:"
        f"fontsize='38+8*sin(t*18)':x='(w-text_w)/2':"
        f"y='675+9*sin(t*20)':enable='between(t,{SCENE_SECONDS-0.95:.2f},{SCENE_SECONDS-0.12:.2f})'",
        f"fade=t=in:st=0:d=0.22",
        f"fade=t=out:st={SCENE_SECONDS-0.22:.2f}:d=0.22",
        "setsar=1",
    ])


@router.get("/api/video/team/ideas")
def discover_video_ideas():
    url = "https://trends.google.com/trending/rss?geo=SE"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NOVA-Cloud"})
    ideas, source_error = [], None
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read(1_500_000)
        root = ET.fromstring(payload)
        for item in root.findall(".//item")[:12]:
            title = (item.findtext("title") or "").strip()
            if title:
                traffic = (item.findtext("{https://trends.google.com/trending/rss}approx_traffic") or "").strip()
                link = (item.findtext("link") or "").strip()
                ideas.append({"title": title[:180], "traffic": traffic,
                              "source": "Google Trends Sverige",
                              "source_url": link or "https://trends.google.com/trending?geo=SE",
                              "angle": "Använd ämnet som inspiration och skapa ett eget innehåll."})
    except Exception as error:
        source_error = str(error)[:240]
    return {"status": "ok" if ideas else "unavailable", "source": "Google Trends Sverige",
            "ideas": ideas,
            "creative_center_url": "https://ads.tiktok.com/business/creativecenter/inspiration/popular/trends/pc/sv",
            "note": "Sökintresse är inte samma sak som verifierade TikTok-visningar.",
            "error": source_error}


@router.post("/api/video/team/create")
async def create_original_video(topic: str = Form(""), mode: str = Form("original"), video_type: str = Form("humor")):
    topic = (topic or "").strip()
    if len(topic) > MAX_PROMPT:
        raise HTTPException(400, f"Ämnet får vara högst {MAX_PROMPT} tecken.")
    if mode not in {"original", "trend"}:
        raise HTTPException(400, "Ogiltigt videoläge.")
    if video_type not in {"humor", "explainer", "tutorial", "promo", "inspiration", "story"}:
        raise HTTPException(400, "Ogiltig videotyp.")
    if not topic:
        topic = "ett intressant ämne"
    job_id = uuid.uuid4().hex[:12]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        beats = _build_script(topic, video_type)
        narration = " ".join(f"{heading}. {line} {caption}" for heading, line, caption, _ in beats)
        narration_path = job_dir / "voice.mp3"
        await edge_tts.Communicate(narration, VOICE).save(str(narration_path))
        clips = []
        attributions = []
        visual_assets = search_commons_images(topic, limit=len(beats))
        for i, (heading, line, caption, kind) in enumerate(beats):
            still = job_dir / f"scene_{i:02}.jpg"
            background_path = None
            if i < len(visual_assets):
                asset_path = job_dir / f"commons_{i:02}.jpg"
                if download_commons_image(visual_assets[i], asset_path):
                    background_path = asset_path
                    attributions.append({key: visual_assets[i].get(key, "") for key in (
                        "title", "page_url", "license", "license_url", "artist", "credit"
                    )})
            _make_scene(still, heading, line, caption, kind, i, background_path)
            clip = job_dir / f"clip_{i:02}.mp4"
            frames = int(SCENE_SECONDS * FPS)
            # Animated camera drift plus subtle, topic-colored comic accents.
            motion = _motion_filter(kind, i, video_type)
            _ffmpeg([
                "-loop", "1", "-i", str(still),
                "-vf", motion,
                "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", str(clip)
            ], timeout=180)
            clips.append(clip)
        concat = job_dir / "clips.txt"
        concat.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
        silent = job_dir / "silent.mp4"
        _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent)], timeout=180)
        output = job_dir / "jarvis_original.mp4"
        _ffmpeg([
            "-i", str(silent), "-i", str(narration_path),
            "-f", "lavfi", "-i", "sine=frequency=392:sample_rate=44100:duration=30",
            "-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.035[music];[voice][music]amix=inputs=2:duration=longest:dropout_transition=2[a]",
            "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", str(output)
        ], timeout=240)
        if not output.is_file() or output.stat().st_size < 10000:
            raise RuntimeError("MP4-filen saknas eller är ofullständig.")
        credits_path = job_dir / "bildkrediter.txt"
        if attributions:
            credit_lines = ["Bildkrediter – Wikimedia Commons", ""]
            for item in attributions:
                credit_lines.extend([
                    item.get("title", "Okänd titel"),
                    f"Upphov: {item.get('artist') or item.get('credit') or 'Ej angiven'}",
                    f"Licens: {item.get('license') or 'Se källsidan'}",
                    f"Licenslänk: {item.get('license_url') or 'Se källsidan'}",
                    f"Källsida: {item.get('page_url') or 'Ej angiven'}",
                    ""
                ])
            credits_path.write_text("\\n".join(credit_lines), encoding="utf-8")
        return {
            "status": "completed", "job_id": job_id, "mode": mode, "video_type": video_type, "topic": topic,
            "script": [{"heading": h, "line": line, "caption": caption}
                       for h, line, caption, _ in beats],
            "format": "9:16", "resolution": "720x1280", "fps": FPS,
            "duration_target_seconds": round(len(beats) * SCENE_SECONDS, 1),
            "voice": VOICE, "video_url": f"/api/video/team/created/{job_id}",
            "visual_source": "Wikimedia Commons + egen grafik" if attributions else "Egen procedural grafik (bildkälla ej tillgänglig)",
            "image_attributions": attributions,
            "credits_url": f"/api/video/team/credits/{job_id}" if attributions else None,
            "message": f"Video skapad ({video_type}) med fem animerade scener, svensk berättarröst och egen ljudmatta."
        }
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(502, f"Kunde inte skapa originalvideon: {str(error)[:700]}")


@router.get("/api/video/team/credits/{job_id}")
def download_video_credits(job_id: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(400, "Ogiltigt jobb-ID.")
    path = OUTPUT_DIR / job_id / "bildkrediter.txt"
    if not path.is_file():
        raise HTTPException(404, "Ingen extern bildkälla användes för den här videon.")
    return FileResponse(path, media_type="text/plain; charset=utf-8", filename="bildkrediter.txt")


@router.get("/api/video/team/created/{job_id}")
def download_original_video(job_id: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(400, "Ogiltigt jobb-ID.")
    path = OUTPUT_DIR / job_id / "jarvis_original.mp4"
    if not path.is_file():
        raise HTTPException(404, "Originalvideon finns inte längre i Render-lagringen.")
    return FileResponse(path, media_type="video/mp4", filename="jarvis-original-tiktok.mp4")
