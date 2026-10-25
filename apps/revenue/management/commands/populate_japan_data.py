import re
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.revenue.models import Auction, CarCategory
from apps.account.models import User

# Comprehensive list of Japanese Auto Auctions
# Each item has: (name, auction_type, venue_key, description)
JAPAN_AUCTIONS = [
    # USS (Used Car System Solutions)
    ("USS Tokyo", "USS", "uss tokyo", "USS Tokyo (Noda, Chiba) - Largest auto auction in Japan"),
    ("USS Yokohama", "USS", "uss yokohama", "USS Yokohama (Kanagawa)"),
    ("USS Nagoya", "USS", "uss nagoya", "USS Nagoya (Tokai, Aichi)"),
    ("USS Osaka", "USS", "uss osaka", "USS Osaka (Osaka)"),
    ("USS Kobe", "USS", "uss kobe", "USS Kobe (Hyogo)"),
    ("USS Fukuoka", "USS", "uss fukuoka", "USS Fukuoka (Fukuoka)"),
    ("USS Sapporo", "USS", "uss sapporo", "USS Sapporo (Ebetsu, Hokkaido)"),
    ("USS Tohoku", "USS", "uss tohoku", "USS Tohoku (Miyagi)"),
    ("USS Shizuoka", "USS", "uss shizuoka", "USS Shizuoka (Fukuroi, Shizuoka)"),
    ("USS Okayama", "USS", "uss okayama", "USS Okayama (Akaiwa, Okayama)"),
    ("USS Gunma", "USS", "uss gunma", "USS Gunma (Fujioka, Gunma)"),
    ("USS Niigata", "USS", "uss niigata", "USS Niigata (Niigata)"),
    ("USS Hokuriku", "USS", "uss hokuriku", "USS Hokuriku (Kanazawa, Ishikawa)"),
    ("USS Shikoku", "USS", "uss shikoku", "USS Shikoku (Kagawa)"),
    ("USS Saitama", "USS", "uss saitama", "USS Saitama (Misato, Saitama)"),
    ("USS Ryutsu", "USS", "uss ryutsu", "USS Ryutsu (Fuefuki, Yamanashi)"),
    ("USS-R Tokyo", "USS", "uss r tokyo", "USS-R Tokyo (Noda, Chiba) - Reusable/economy vehicles"),
    ("USS-R Nagoya", "USS", "uss r nagoya", "USS-R Nagoya (Aichi) - Reusable/economy vehicles"),

    # TAA (Toyota Auto Auction)
    ("TAA Tokyo", "TAA", "taa tokyo", "TAA Tokyo (Kanto yard)"),
    ("TAA Kanto", "TAA", "taa kanto", "TAA Kanto (Chiba)"),
    ("TAA Yokohama", "TAA", "taa yokohama", "TAA Yokohama (Kanagawa)"),
    ("TAA Chubu", "TAA", "taa chubu", "TAA Chubu (Tokai, Aichi)"),
    ("TAA Kansai", "TAA", "taa kansai", "TAA Kansai (Nishinomiya, Hyogo)"),
    ("TAA Hiroshima", "TAA", "taa hiroshima", "TAA Hiroshima (Hiroshima)"),
    ("TAA Kyushu", "TAA", "taa kyushu", "TAA Kyushu (Tosu, Saga)"),
    ("TAA Minami Kyushu", "TAA", "taa minami kyushu", "TAA Minami Kyushu (Kagoshima)"),
    ("TAA Shikoku", "TAA", "taa shikoku", "TAA Shikoku (Matsuyama, Ehime)"),
    ("TAA Tohoku", "TAA", "taa tohoku", "TAA Tohoku (Koriyama, Fukushima)"),
    ("TAA Hokkaido", "TAA", "taa hokkaido", "TAA Hokkaido (Tomakomai, Hokkaido)"),

    # JU Group (Japan Used Car Dealers Association)
    ("JU Tokyo", "JU", "ju tokyo", "JU Tokyo (Saitama/Tokyo)"),
    ("JU Saitama", "JU", "ju saitama", "JU Saitama (Iwatatsuki, Saitama)"),
    ("JU Kanagawa", "JU", "ju kanagawa", "JU Kanagawa (Aiko, Kanagawa)"),
    ("JU Chiba", "JU", "ju chiba", "JU Chiba (Inzai, Chiba)"),
    ("JU Ibaraki", "JU", "ju ibaraki", "JU Ibaraki (Ibaraki)"),
    ("JU Tochigi", "JU", "ju tochigi", "JU Tochigi (Utsunomiya, Tochigi)"),
    ("JU Gunma", "JU", "ju gunma", "JU Gunma (Takasaki, Gunma)"),
    ("JU Shizuoka", "JU", "ju shizuoka", "JU Shizuoka (Fukuroi, Shizuoka)"),
    ("JU Aichi", "JU", "ju aichi", "JU Aichi (Inazawa, Aichi)"),
    ("JU Gifu", "JU", "ju gifu", "JU Gifu (Hashima, Gifu)"),
    ("JU Mie", "JU", "ju mie", "JU Mie (Tsu, Mie)"),
    ("JU Niigata", "JU", "ju niigata", "JU Niigata (Niigata)"),
    ("JU Nagano", "JU", "ju nagano", "JU Nagano (Nagano)"),
    ("JU Yamanashi", "JU", "ju yamanashi", "JU Yamanashi (Yamanashi)"),
    ("JU Osaka", "JU", "ju osaka", "JU Osaka (Takatsuki, Osaka)"),
    ("JU Hyogo", "JU", "ju hyogo", "JU Hyogo (Kobe, Hyogo)"),
    ("JU Kyoto", "JU", "ju kyoto", "JU Kyoto (Fushimi, Kyoto)"),
    ("JU Nara", "JU", "ju nara", "JU Nara (Nara)"),
    ("JU Shiga", "JU", "ju shiga", "JU Shiga (Shiga)"),
    ("JU Wakayama", "JU", "ju wakayama", "JU Wakayama (Wakayama)"),
    ("JU Hiroshima", "JU", "ju hiroshima", "JU Hiroshima (Hiroshima)"),
    ("JU Okayama", "JU", "ju okayama", "JU Okayama (Okayama)"),
    ("JU Yamaguchi", "JU", "ju yamaguchi", "JU Yamaguchi (Yamaguchi)"),
    ("JU Shimane", "JU", "ju shimane", "JU Shimane (Shimane)"),
    ("JU Tottori", "JU", "ju tottori", "JU Tottori (Tottori)"),
    ("JU Fukuoka", "JU", "ju fukuoka", "JU Fukuoka (Koga, Fukuoka)"),
    ("JU Kumamoto", "JU", "ju kumamoto", "JU Kumamoto (Kumamoto)"),
    ("JU Oita", "JU", "ju oita", "JU Oita (Oita)"),
    ("JU Nagasaki", "JU", "ju nagasaki", "JU Nagasaki (Isahaya, Nagasaki)"),
    ("JU Miyazaki", "JU", "ju miyazaki", "JU Miyazaki (Miyazaki)"),
    ("JU Kagoshima", "JU", "ju kagoshima", "JU Kagoshima (Kagoshima)"),
    ("JU Okinawa", "JU", "ju okinawa", "JU Okinawa (Okinawa)"),
    ("JU Hokkaido", "JU", "ju hokkaido", "JU Hokkaido (Sapporo, Hokkaido)"),
    ("JU Asahikawa", "JU", "ju asahikawa", "JU Asahikawa (Hokkaido)"),
    ("JU Kushiro", "JU", "ju kushiro", "JU Kushiro (Hokkaido)"),
    ("JU Obihiro", "JU", "ju obihiro", "JU Obihiro (Hokkaido)"),
    ("JU Hakodate", "JU", "ju hakodate", "JU Hakodate (Hokkaido)"),
    ("JU Miyagi", "JU", "ju miyagi", "JU Miyagi (Sendai, Miyagi)"),
    ("JU Fukushima", "JU", "ju fukushima", "JU Fukushima (Koriyama, Fukushima)"),
    ("JU Aomori", "JU", "ju aomori", "JU Aomori (Aomori)"),
    ("JU Iwate", "JU", "ju iwate", "JU Iwate (Morioka, Iwate)"),
    ("JU Akita", "JU", "ju akita", "JU Akita (Akita)"),
    ("JU Yamagata", "JU", "ju yamagata", "JU Yamagata (Yamagata)"),
    ("JU Toyama", "JU", "ju toyama", "JU Toyama (Toyama)"),
    ("JU Ishikawa", "JU", "ju ishikawa", "JU Ishikawa (Ishikawa)"),
    ("JU Fukui", "JU", "ju fukui", "JU Fukui (Fukui)"),
    ("JU Kagawa", "JU", "ju kagawa", "JU Kagawa (Takamatsu, Kagawa)"),
    ("JU Tokushima", "JU", "ju tokushima", "JU Tokushima (Tokushima)"),
    ("JU Ehime", "JU", "ju ehime", "JU Ehime (Matsuyama, Ehime)"),
    ("JU Kochi", "JU", "ju kochi", "JU Kochi (Kochi)"),

    # ARAI (Arai Auto Auction)
    ("ARAI Bayside", "ARAI", "arai bayside", "ARAI Bayside (Kawasaki, Kanagawa)"),
    ("ARAI Oyama", "ARAI", "arai oyama", "ARAI Oyama (Oyama, Tochigi) - Passenger & Van/Truck"),
    ("ARAI Sendai", "ARAI", "arai sendai", "ARAI Sendai (Miyagi)"),
    ("ARAI Fukuoka", "ARAI", "arai fukuoka", "ARAI Fukuoka (Fukuoka)"),

    # CAA (Chubu Auto Auction)
    ("CAA Chubu", "CAA", "caa chubu", "CAA Chubu (Toyota City, Aichi)"),
    ("CAA Tokyo", "CAA", "caa tokyo", "CAA Tokyo (Inzai, Chiba)"),
    ("CAA Gifu", "CAA", "caa gifu", "CAA Gifu (Hashima, Gifu)"),
    ("CAA Tohoku", "CAA", "caa tohoku", "CAA Tohoku (Ohira, Miyagi)"),

    # NAA (Nissan Auto Auction)
    ("NAA Tokyo", "NAA", "naa tokyo", "NAA Tokyo (Yokohama, Kanagawa)"),
    ("NAA Nagoya", "NAA", "naa nagoya", "NAA Nagoya (Tokai, Aichi)"),
    ("NAA Osaka", "NAA", "naa osaka", "NAA Osaka (Settsu, Osaka)"),
    ("NAA Fukuoka", "NAA", "naa fukuoka", "NAA Fukuoka (Fukuoka)"),

    # Honda AA (Honda Auto Auction)
    ("Honda AA Tokyo", "Honda", "honda aa tokyo", "Honda AA Tokyo (Tokyo/Chiba)"),
    ("Honda AA Nagoya", "Honda", "honda aa nagoya", "Honda AA Nagoya (Aichi)"),
    ("Honda AA Kansai", "Honda", "honda aa kansai", "Honda AA Kansai (Kobe, Hyogo)"),
    ("Honda AA Kyushu", "Honda", "honda aa kyushu", "Honda AA Kyushu (Fukuoka)"),
    ("Honda AA Sendai", "Honda", "honda aa sendai", "Honda AA Sendai (Miyagi)"),
    ("Honda AA Hokkaido", "Honda", "honda aa hokkaido", "Honda AA Hokkaido (Sapporo)"),

    # HAA (Hanaten Auto Auction)
    ("HAA Kobe", "HAA", "haa kobe", "HAA Kobe (Kobe, Hyogo) - Major Saturday auction"),
    ("HAA Osaka", "HAA", "haa osaka", "HAA Osaka (Osaka)"),

    # LAA (Lexus / Local Auto Auction)
    ("LAA Kansai", "LAA", "laa kansai", "LAA Kansai (Nishinomiya, Hyogo)"),
    ("LAA Shikoku", "LAA", "laa shikoku", "LAA Shikoku (Sakaide, Kagawa)"),
    ("LAA Okayama", "LAA", "laa okayama", "LAA Okayama (Okayama)"),
    ("LAA Tokyo", "LAA", "laa tokyo", "LAA Tokyo"),
    ("LAA Nagoya", "LAA", "laa nagoya", "LAA Nagoya"),

    # SAA (Subaru / Sapporo Auto Auction)
    ("SAA Tokyo", "SAA", "saa tokyo", "SAA Tokyo"),
    ("SAA Nagoya", "SAA", "saa nagoya", "SAA Nagoya"),
    ("SAA Osaka", "SAA", "saa osaka", "SAA Osaka"),
    ("SAA Hamamatsu", "SAA", "saa hamamatsu", "SAA Hamamatsu (Hamamatsu, Shizuoka)"),
    ("SAA Sapporo", "SAA", "saa sapporo", "SAA Sapporo (Hokkaido)"),

    # BayAuc (Bayside Auto Auction)
    ("Bay Auc Osaka", "BayAuc", "bay auc osaka", "Bay Auc Osaka (Osaka) - Established independent venue"),
    ("Bay Auc Tokyo", "BayAuc", "bay auc tokyo", "Bay Auc Tokyo"),
    ("Bay Auc Nagoya", "BayAuc", "bay auc nagoya", "Bay Auc Nagoya"),

    # BCN (BCN Auto Auction)
    ("BCN Tokyo", "BCN", "bcn tokyo", "BCN Tokyo (Fukaya, Saitama)"),
    ("BCN Kansai", "BCN", "bcn kansai", "BCN Kansai (Osaka)"),

    # MIRIVE
    ("MIRIVE Saitama", "MIRIVE", "mirive saitama", "MIRIVE Saitama (Fukaya, Saitama)"),
    ("MIRIVE Osaka", "MIRIVE", "mirive osaka", "MIRIVE Osaka (Kobe/Osaka)"),
    ("MIRIVE Aichi", "MIRIVE", "mirive aichi", "MIRIVE Aichi"),

    # ZIP
    ("ZIP Osaka", "ZIP", "zip osaka", "ZIP Osaka (Osaka)"),
    ("ZIP Tokyo", "ZIP", "zip tokyo", "ZIP Tokyo (Tokyo)"),

    # KCAA (Kyushu Central Auto Auction)
    ("KCAA Fukuoka", "KCAA", "kcaa fukuoka", "KCAA Fukuoka (Fukuoka)"),
    ("KCAA Minami-Kyushu", "KCAA", "kcaa minami", "KCAA Minami-Kyushu (Ebino, Miyazaki)"),
    ("KCAA Yamaguchi", "KCAA", "kcaa yamaguchi", "KCAA Yamaguchi (Sanyo-Onoda, Yamaguchi)"),

    # ORIX (Orix Auto Auction)
    ("ORIX Atsugi", "ORIX", "orix atsugi", "ORIX Atsugi (Kanagawa) - Ex-fleet and lease returns"),
    ("ORIX Kobe", "ORIX", "orix kobe", "ORIX Kobe (Hyogo)"),
    ("ORIX Nagoya", "ORIX", "orix nagoya", "ORIX Nagoya (Aichi)"),
    ("ORIX Fukuoka", "ORIX", "orix fukuoka", "ORIX Fukuoka (Fukuoka)"),
    ("ORIX Sendai", "ORIX", "orix sendai", "ORIX Sendai (Miyagi)"),

    # JAA (Japan Automobile Auction)
    ("JAA Tokyo", "JAA", "jaa tokyo", "JAA Tokyo (Koto-ku, Tokyo)"),
    ("JAA Tsukuba", "JAA", "jaa tsukuba", "JAA Tsukuba (Ibaraki)"),

    # Other Major Networks
    ("Aucnet Satellite", "AUCNET", "aucnet", "Aucnet Satellite / Digital Auction Network"),
    ("SMAP Tokyo", "SMAP", "smap tokyo", "SMAP Tokyo (Sumitomo Mitsui Auto)"),
    ("SMAP Osaka", "SMAP", "smap osaka", "SMAP Osaka (Sumitomo Mitsui Auto)"),
    ("Zero Chubu", "Zero", "zero chubu", "Zero Chubu Auto Auction"),
    ("Zero Osaka", "Zero", "zero osaka", "Zero Osaka Auto Auction"),
    ("Zero Shonan", "Zero", "zero shonan", "Zero Shonan Auto Auction"),
    ("HERO Tokyo", "HERO", "hero tokyo", "HERO Auto Auction (Tokyo)"),
]

# Comprehensive list of Japanese car manufacturers and models
JAPAN_CARS = {
    "TOYOTA": [
        # Compact / Hatchbacks
        ("Aqua", "Compact Hybrid Hatchback"),
        ("Prius", "Hybrid Sedan / Liftback"),
        ("Prius Alpha", "Hybrid MPV / Wagon"),
        ("Prius PHV", "Plug-in Hybrid"),
        ("Yaris", "Compact Hatchback"),
        ("Yaris Cross", "Compact SUV"),
        ("GR Yaris", "Hot Hatch / Rally Performance"),
        ("Corolla", "Sedan"),
        ("Corolla Axio", "Compact Sedan"),
        ("Corolla Fielder", "Station Wagon"),
        ("Corolla Sport", "Hatchback"),
        ("Corolla Touring", "Station Wagon"),
        ("Corolla Cross", "Crossover SUV"),
        ("Corolla Rumion", "Boxy Compact Wagon"),
        ("Passo", "Subcompact Hatchback"),
        ("Passo Sette", "Compact MPV"),
        ("Vitz", "Subcompact Hatchback"),
        ("bB", "Boxy Subcompact"),
        ("ist", "Subcompact Crossover Hatchback"),
        ("Roomy", "Tall Compact Wagon"),
        ("Tank", "Tall Compact Wagon"),
        ("Porte", "Sliding-door Compact"),
        ("Spade", "Sliding-door Compact"),
        ("Ractis", "High-roof Subcompact"),
        ("Auris", "Hatchback"),
        ("Blade", "Premium Hatchback"),
        ("Allex", "Hatchback"),
        ("Starlet", "Classic Hatchback"),
        ("Glanza", "Compact Hatchback"),
        ("Aygo X", "Urban Crossover"),

        # Sedans & Luxury
        ("Camry", "Mid-size Sedan"),
        ("Camry Hybrid", "Mid-size Hybrid Sedan"),
        ("Crown", "Executive Sedan / Crossover"),
        ("Crown Athlete", "Sports Luxury Sedan"),
        ("Crown Royal", "Luxury Sedan"),
        ("Crown Majesta", "Flagship V8 Luxury Sedan"),
        ("Crown Crossover", "Modern Crossover"),
        ("Crown Sport", "Sport SUV"),
        ("Crown Sedan", "Full-size Executive Sedan"),
        ("Century", "Ultra-Luxury Flagship V12/V8"),
        ("Mirai", "Hydrogen Fuel Cell Sedan"),
        ("Mark II", "Mid-size RWD Sedan"),
        ("Mark X", "Mid-size RWD Sports Sedan"),
        ("Mark X Zio", "Premium Crossover Wagon"),
        ("Chaser", "Sports Sedan (Tourer V)"),
        ("Cresta", "Luxury Mid-size Sedan"),
        ("Altezza", "Sports Sedan (IS predecessor)"),
        ("Aristo", "Twin-Turbo Luxury Sedan (GS)"),
        ("Soarer", "Grand Tourer Coupe/Convertible"),
        ("Verossa", "Sports Sedan"),
        ("Brevis", "Compact Executive Sedan"),
        ("Progres", "Compact Executive Sedan"),
        ("Celsior", "Flagship Luxury Sedan (LS)"),
        ("Allion", "Compact Executive Sedan"),
        ("Premio", "Compact Executive Sedan"),
        ("Belta", "Subcompact Sedan"),
        ("Avalon", "Full-size Sedan"),
        ("SAI", "Hybrid Executive Sedan"),
        ("Avensis", "Sedan / Station Wagon"),
        ("Caldina", "Sports Wagon (GT-Four)"),

        # SUVs & 4WD
        ("RAV4", "Compact / Mid-size SUV"),
        ("RAV4 PHV", "Plug-in Hybrid SUV"),
        ("Harrier", "Mid-size Luxury Crossover"),
        ("Harrier Hybrid", "Mid-size Luxury Hybrid Crossover"),
        ("C-HR", "Subcompact Crossover"),
        ("Raize", "Compact Crossover SUV"),
        ("Rush", "Mini 4WD SUV"),
        ("Vanguard", "Mid-size 7-seater SUV"),
        ("Land Cruiser 300", "Full-size Luxury 4WD"),
        ("Land Cruiser 250", "All-Terrain 4WD (New Prado)"),
        ("Land Cruiser 200", "Full-size Luxury 4WD"),
        ("Land Cruiser 100", "Full-size 4WD"),
        ("Land Cruiser 80", "Heavy Duty 4WD"),
        ("Land Cruiser 70", "Heavy Duty Classic 4WD"),
        ("Land Cruiser Prado", "Mid-size 4WD SUV"),
        ("Hilux Surf", "Rugged 4WD SUV (4Runner)"),
        ("Fortuner", "Mid-size 4WD SUV"),
        ("Highlander", "Mid-size 3-row SUV"),
        ("Kluger", "Mid-size Crossover SUV"),
        ("4Runner", "Mid-size All-Terrain SUV"),
        ("Sequoia", "Full-size 3-row SUV"),
        ("Venza", "Mid-size Crossover SUV"),
        ("bZ4X", "All-Electric SUV"),
        ("Urban Cruiser", "Compact SUV"),

        # Minivans & MPVs
        ("Alphard", "Flagship Luxury Minivan"),
        ("Vellfire", "Flagship Sports Luxury Minivan"),
        ("Noah", "Mid-size Minivan"),
        ("Voxy", "Mid-size Minivan"),
        ("Esquire", "Premium Mid-size Minivan"),
        ("Sienta", "Compact 7-seater Minivan"),
        ("Estima", "Previa / Egg-shaped MPV"),
        ("Estima Hybrid", "Hybrid MPV"),
        ("HiAce", "Commercial / Passenger Van"),
        ("HiAce Commuter", "15-passenger Van"),
        ("Regius", "Premium Van"),
        ("RegiusAce", "Cargo / Passenger Van"),
        ("Granace", "Full-size Luxury Minivan"),
        ("Granvia", "Full-size Minivan"),
        ("TownAce", "Compact Van / Truck"),
        ("LiteAce", "Compact Van / Truck"),
        ("Isis", "Panoramic-door Minivan"),
        ("Wish", "Sporty 7-seater MPV"),
        ("Ipsum", "Mid-size 7-seater MPV"),
        ("Gaia", "Mid-size MPV"),
        ("Innova", "Multi-purpose Vehicle"),
        ("Avanza", "Compact MPV"),
        ("Veloz", "Premium Compact MPV"),
        ("Probox", "Commercial Station Wagon"),
        ("Succeed", "Commercial Station Wagon"),

        # Trucks
        ("Hilux", "Mid-size Pickup Truck"),
        ("Dyna", "Light/Medium Commercial Truck"),
        ("ToyoAce", "Light Commercial Truck"),
        ("Tacoma", "Mid-size Pickup"),
        ("Tundra", "Full-size Pickup"),

        # Sports Cars
        ("GR Supra", "Flagship RWD Sports Car"),
        ("Supra", "Classic Turbo Sports Car (A80/A70)"),
        ("GR86", "Lightweight RWD Sports Coupe"),
        ("86", "Lightweight RWD Sports Coupe"),
        ("GR Corolla", "AWD Hot Hatch"),
        ("Celica", "Sports Coupe (GT-Four)"),
        ("MR2", "Mid-engine Sports Car (SW20)"),
        ("MR-S", "Mid-engine Roadster (ZZW30)"),
        ("2000GT", "Classic Supercar"),
        ("AE86 Sprinter Trueno", "Iconic RWD Sports Coupe"),
        ("AE86 Corolla Levin", "Iconic RWD Sports Coupe"),

        # Kei Cars (OEM Daihatsu)
        ("Pixis Epoch", "Kei Hatchback"),
        ("Pixis Space", "Kei Box Wagon"),
        ("Pixis Joy", "Kei Crossover"),
        ("Pixis Mega", "Super Height Kei Wagon"),
        ("Pixis Van", "Kei Microvan"),
        ("Pixis Truck", "Kei Microtruck"),
        ("Copen GR Sport", "Kei Roadster"),
    ],

    "NISSAN": [
        # Compact / Hatchbacks
        ("Note", "Compact Hatchback"),
        ("Note e-POWER", "Hybrid Compact Hatchback"),
        ("Note Aura", "Premium Compact Hatchback"),
        ("March", "Subcompact Hatchback (Micra)"),
        ("Tiida", "Compact Hatchback"),
        ("Tiida Latio", "Compact Sedan"),
        ("Cube", "Boxy Urban Compact"),
        ("Leaf", "Electric Hatchback"),
        ("Ariya", "All-Electric Crossover SUV"),
        ("Sakura", "All-Electric Kei Car"),
        ("Pulsar", "Compact Hatchback (GTI-R)"),
        ("Pulsar GTI-R", "AWD Turbo Rally Homologation"),

        # Sedans & Luxury
        ("Skyline", "Sports Sedan"),
        ("Skyline GT-R", "AWD Twin-Turbo Supercar (R32/R33/R34)"),
        ("GT-R", "Supercar (R35)"),
        ("Fuga", "Executive Luxury Sedan"),
        ("Fuga Hybrid", "Executive Hybrid Sedan"),
        ("Cima", "Flagship Luxury V8 Sedan"),
        ("Cima Hybrid", "Flagship Hybrid Luxury Sedan"),
        ("Teana", "Mid-size Luxury Sedan"),
        ("Sylphy", "Compact Sedan"),
        ("Bluebird", "Classic Mid-size Sedan"),
        ("Bluebird Sylphy", "Compact Executive Sedan"),
        ("Cedric", "Classic Luxury RWD Sedan"),
        ("Gloria", "Classic Luxury RWD Sedan"),
        ("Laurel", "Mid-size RWD Executive Sedan"),
        ("Cefiro", "Mid-size Executive Sedan"),
        ("Primera", "Sport Touring Sedan / Wagon"),
        ("Sunny", "Subcompact Sedan"),
        ("Latio", "Subcompact Sedan"),
        ("Almera", "Subcompact Sedan"),
        ("Sentra", "Compact Sedan"),
        ("Altima", "Mid-size Sedan"),
        ("Maxima", "Full-size Sports Sedan"),
        ("President", "Imperial Flagship V8 Limousine"),
        ("Stagea", "Performance Sports Wagon (260RS)"),
        ("Wingroad", "Compact Station Wagon"),
        ("AD Van", "Commercial Station Wagon"),
        ("AD Expert", "Commercial Station Wagon"),
        ("Avenir", "Station Wagon"),

        # SUVs & Crossovers
        ("X-Trail", "Mid-size SUV"),
        ("X-Trail e-POWER", "Hybrid Mid-size SUV"),
        ("Dualis", "Compact Crossover (Qashqai)"),
        ("Qashqai", "Compact Crossover"),
        ("Kicks", "Subcompact Crossover"),
        ("Kicks e-POWER", "Hybrid Subcompact Crossover"),
        ("Juke", "Subcompact Crossover"),
        ("Murano", "Mid-size Luxury Crossover"),
        ("Pathfinder", "Mid-size 3-row SUV"),
        ("Patrol", "Full-size 4WD SUV (Safari)"),
        ("Safari", "Heavy-duty 4WD Off-roader"),
        ("Armada", "Full-size V8 SUV"),
        ("Terra", "Mid-size 4WD SUV"),
        ("Skyline Crossover", "Luxury Performance Crossover (EX37)"),

        # Minivans & Commercial
        ("Serena", "Mid-size Minivan"),
        ("Serena e-POWER", "Hybrid Mid-size Minivan"),
        ("Elgrand", "Flagship Luxury Minivan"),
        ("Lafesta", "Compact 7-seater Minivan"),
        ("Lafesta Highway Star", "Sport Minivan"),
        ("Presage", "Mid-size Minivan"),
        ("Bassara", "Mid-size Minivan"),
        ("NV200 Vanette", "Compact Commercial / Passenger Van"),
        ("NV350 Caravan", "Full-size Van"),
        ("Caravan", "Commercial / Passenger Van"),
        ("NV100 Clipper", "Kei Microvan"),
        ("NV100 Clipper Rio", "Passenger Kei Van"),
        ("NT100 Clipper", "Kei Microtruck"),
        ("Atlas", "Light / Medium Commercial Truck"),
        ("Cabstar", "Light Commercial Truck"),
        ("Navara", "Mid-size Pickup Truck"),
        ("Frontier", "Mid-size Pickup Truck"),
        ("Titan", "Full-size Pickup Truck"),

        # Sports Cars
        ("Fairlady Z", "Sports Coupe (RZ34 / 370Z / 350Z)"),
        ("370Z", "Sports Coupe / Roadster"),
        ("350Z", "Sports Coupe / Roadster"),
        ("300ZX", "Twin-Turbo Sports Coupe (Z32)"),
        ("Silvia", "RWD Sports Coupe (S15/S14/S13)"),
        ("180SX", "Fastback RWD Sports Coupe"),
        ("200SX", "RWD Sports Coupe"),
        ("240SX", "RWD Sports Coupe"),

        # Kei Cars
        ("Dayz", "Kei Hatchback"),
        ("Dayz Roox", "Tall Height Kei Wagon"),
        ("Roox", "Super Height Kei Wagon"),
        ("Otti", "Kei Hatchback"),
        ("Moco", "Kei Hatchback"),
        ("Kix", "Mini 4WD Kei SUV"),
        ("Pino", "Compact Kei Hatchback"),
    ],

    "HONDA": [
        # Compact / Hatchbacks
        ("Fit", "Subcompact Hatchback (Jazz)"),
        ("Fit Hybrid", "Hybrid Subcompact Hatchback"),
        ("Fit Crosstar", "Crossover Compact Hatchback"),
        ("Fit Shuttle", "Compact Wagon"),
        ("Shuttle", "Compact Hybrid Station Wagon"),
        ("City", "Subcompact Sedan / Hatchback"),
        ("Civic", "Compact Hatchback / Sedan"),
        ("Civic Hatchback", "5-door Sport Hatchback"),
        ("Civic Sedan", "Compact Sedan"),
        ("Civic Type R", "High-Performance Hot Hatch"),
        ("Civic e:HEV", "Hybrid Sport Hatchback"),
        ("Insight", "Dedicated Hybrid Sedan / Hatchback"),
        ("CR-Z", "Sport Hybrid Coupe"),
        ("Clarity", "PHEV / Fuel Cell Sedan"),
        ("Honda e", "Retro-styled Electric City Car"),

        # Sedans & Luxury
        ("Accord", "Mid-size Executive Sedan"),
        ("Accord Hybrid", "Mid-size Hybrid Sedan"),
        ("Accord Euro-R", "Sports Sedan"),
        ("Accord Tourer", "Station Wagon"),
        ("Inspire", "Mid-size Luxury Sedan"),
        ("Legend", "Flagship Luxury Sedan (SH-AWD)"),
        ("Grace", "Compact Hybrid Sedan"),
        ("Torneo", "Sports Sedan"),
        ("Integra", "Sports Coupe / Sedan"),
        ("Integra Type R", "High-Revving Track-focused Coupe (DC2/DC5)"),
        ("Prelude", "Sports Coupe"),

        # SUVs & Crossovers
        ("Vezel", "Subcompact Crossover (HR-V)"),
        ("Vezel e:HEV", "Hybrid Subcompact Crossover"),
        ("HR-V", "Subcompact Crossover"),
        ("CR-V", "Compact / Mid-size SUV"),
        ("CR-V e:HEV", "Hybrid Mid-size SUV"),
        ("ZR-V", "Sport Crossover SUV"),
        ("WR-V", "Entry Crossover SUV"),
        ("Passport", "Mid-size All-Terrain SUV"),
        ("Pilot", "3-row Mid-size SUV"),
        ("Element", "Boxy Utility Crossover"),
        ("Crossroad", "Boxy 7-seater SUV"),
        ("MDX", "Mid-size Luxury SUV"),

        # Minivans & MPVs
        ("Stepwgn", "Mid-size Box Minivan"),
        ("Stepwgn Spada", "Aero Sports Minivan"),
        ("Stepwgn Air", "Modern Family Minivan"),
        ("Stepwgn e:HEV", "Hybrid Box Minivan"),
        ("Freed", "Compact 6/7-seater Minivan"),
        ("Freed+", "Compact 5-seater Activity Wagon"),
        ("Freed Spike", "Compact Activity Wagon"),
        ("Freed e:HEV", "Hybrid Compact Minivan"),
        ("Odyssey", "Low-roof Executive Minivan"),
        ("Odyssey Absolute", "Sport Luxury Minivan"),
        ("Odyssey Hybrid", "Hybrid Executive Minivan"),
        ("Elysion", "Flagship Luxury Minivan"),
        ("Elysion Prestige", "V6 Flagship Minivan"),
        ("Stream", "Sporty 7-seater Minivan"),
        ("Edix", "3x2 6-seater Compact MPV (FR-V)"),
        ("Mobilio", "Compact 7-seater MPV"),
        ("Mobilio Spike", "Compact Utility MPV"),
        ("Jade", "Low-slung 6-seater Wagon / MPV"),

        # Sports Cars
        ("NSX", "Mid-Engine Supercar (NA1/NA2/NC1)"),
        ("NSX-R", "Track Lightweight Supercar"),
        ("S2000", "High-Revving 9000rpm RWD Roadster (AP1/AP2)"),
        ("S660", "Mid-Engine Kei Roadster"),
        ("Beat", "Classic Mid-Engine Kei Roadster"),
        ("CR-X", "Lightweight Sport Hatchback"),
        ("CR-X del Sol", "Targa-top Roadster"),

        # Kei Cars
        ("N-BOX", "Super Height Kei Wagon (Best-seller)"),
        ("N-BOX Custom", "Aero Super Height Kei Wagon"),
        ("N-BOX Slash", "Chopped-roof Style Kei Wagon"),
        ("N-WGN", "Tall Height Kei Wagon"),
        ("N-WGN Custom", "Aero Tall Height Kei Wagon"),
        ("N-ONE", "Retro-styled Kei Hatchback"),
        ("N-VAN", "Commercial / Lifestyle Kei Van"),
        ("Life", "Kei Hatchback"),
        ("Life Dunk", "Turbo Kei Hatchback"),
        ("Zest", "Tall Kei Hatchback"),
        ("Zest Spark", "Sporty Kei Hatchback"),
        ("That-s", "Tall Box Kei Car"),
        ("Vamos", "Kei Microvan"),
        ("Vamos Hobio", "High-roof Kei Microvan"),
        ("Acty Van", "Mid-engine Kei Microvan"),
        ("Acty Truck", "Mid-engine Kei Microtruck"),
    ],

    "MAZDA": [
        # Compact / Hatchbacks
        ("Mazda2", "Subcompact Hatchback"),
        ("Demio", "Subcompact Hatchback (Best-seller)"),
        ("Mazda3", "Compact Hatchback / Sedan"),
        ("Axela", "Compact Hatchback / Sedan"),
        ("Mazda3 Fastback", "Sport Hatchback"),
        ("Mazda3 Sedan", "Compact Sedan"),
        ("Mazda6", "Mid-size Executive Sedan"),
        ("Atenza", "Mid-size Executive Sedan"),
        ("Atenza Wagon", "Mid-size Station Wagon"),
        ("Mazdaspeed 3", "Turbo Hot Hatch (Mazdaspeed Axela)"),
        ("Mazdaspeed 6", "Turbo AWD Sports Sedan (Mazdaspeed Atenza)"),
        ("Verisa", "Premium Tall Subcompact"),
        ("Familia", "Classic Compact"),
        ("Familia Van", "Commercial Wagon"),

        # SUVs & Crossovers
        ("CX-3", "Subcompact Crossover"),
        ("CX-30", "Compact Crossover SUV"),
        ("CX-5", "Mid-size Crossover SUV (Global Flagship)"),
        ("CX-50", "Rugged Outdoor Crossover SUV"),
        ("CX-60", "RWD-platform Premium Mid-size SUV"),
        ("CX-70", "Wide-body 2-row Premium SUV"),
        ("CX-8", "3-row Mid-size Crossover SUV"),
        ("CX-80", "3-row RWD-platform Premium SUV"),
        ("CX-9", "Full-size 3-row Crossover SUV"),
        ("CX-90", "Full-size 3-row Flagship SUV"),
        ("MX-30", "Electric / Rotary Hybrid Crossover"),
        ("CX-7", "Sport Crossover SUV"),
        ("Tribute", "Compact 4WD SUV"),

        # Minivans & Commercial
        ("Biante", "Tall High-roof Minivan"),
        ("MPV", "Mid-size 7-seater Minivan"),
        ("Premacy", "Compact 7-seater Minivan (Mazda5)"),
        ("Bongo", "Commercial Cab-over Van / Truck"),
        ("Bongo Brawny", "Heavy Commercial Van"),
        ("Bongo Friendee", "Auto Free Top Camper Van"),
        ("Titan", "Light / Medium Commercial Truck"),

        # Sports Cars
        ("Roadster", "World's Best-selling 2-seater Convertible (Miata)"),
        ("MX-5 Miata", "Lightweight RWD Sports Roadster"),
        ("Roadster RF", "Retractable Fastback Roadster"),
        ("RX-7", "Twin-Turbo Rotary Sports Car (FD3S / FC3S)"),
        ("RX-8", "Freestyle-door Rotary Sports Coupe"),
        ("Eunos Cosmo", "Triple-Rotor Twin-Turbo Luxury GT"),
        ("Autozam AZ-1", "Gullwing Mid-engine Kei Sports Car"),

        # Kei Cars
        ("Carol", "Kei Hatchback"),
        ("Flair", "Tall Kei Wagon"),
        ("Flair Custom Style", "Aero Kei Wagon"),
        ("Flair Wagon", "Super Height Kei Wagon"),
        ("Flair Crossover", "Crossover Kei Car"),
        ("Scrum Van", "Kei Microvan"),
        ("Scrum Truck", "Kei Microtruck"),
        ("AZ-Wagon", "Tall Kei Wagon"),
        ("Spiano", "Retro Kei Car"),
    ],

    "MITSUBISHI": [
        # Compact / Hatchbacks
        ("Mirage", "Subcompact Hatchback"),
        ("Colt", "Subcompact Hatchback"),
        ("Colt Plus", "Extended Compact Wagon"),
        ("Colt Ralliart Version-R", "Turbo Hot Hatch"),
        ("i", "Rear Mid-engine Subcompact"),
        ("i-MiEV", "Pioneer Electric City Car"),
        ("Minica", "Kei Hatchback"),
        ("Toppo", "High-roof Kei Car"),
        ("Toppo BJ", "High-roof Kei Car"),

        # Sedans & Luxury
        ("Lancer", "Compact Sedan"),
        ("Lancer Evolution", "Rally Legend AWD Turbo (Evo I to X)"),
        ("Lancer Evolution Wagon", "Ultra-rare AWD Turbo Wagon"),
        ("Lancer Cargo", "Commercial Station Wagon"),
        ("Galant", "Mid-size Sedan (VR-4)"),
        ("Galant Fortis", "Sports Sedan"),
        ("Galant Fortis Sportback", "5-door Sportback"),
        ("Diamante", "Executive V6 Sedan / Wagon"),
        ("Proudia", "Executive Luxury Sedan"),
        ("Dignity", "Flagship Luxury Limousine"),
        ("Attrage", "Subcompact Sedan"),

        # SUVs & 4WD
        ("Outlander", "Mid-size 3-row SUV"),
        ("Outlander PHEV", "Plug-in Hybrid AWD SUV"),
        ("Eclipse Cross", "Coupe Crossover SUV"),
        ("Eclipse Cross PHEV", "Plug-in Hybrid Crossover"),
        ("RVR", "Compact Crossover (ASX / Outlander Sport)"),
        ("ASX", "Compact Crossover SUV"),
        ("Pajero", "World Rally Icon Full-size 4WD"),
        ("Pajero Short", "3-door Short-wheelbase 4WD"),
        ("Pajero Long", "5-door 7-seater 4WD"),
        ("Pajero Evolution", "Dakar Homologation 4WD Beast"),
        ("Pajero Sport", "Challenger / Montero Sport 4WD"),
        ("Pajero io", "Compact 4WD SUV"),
        ("Pajero Mini", "Kei 4WD Mini-SUV"),
        ("Pajero Junior", "Compact 4WD SUV"),
        ("Airtrek", "Crossover SUV (Turbo-R)"),
        ("Challenger", "Off-road 4WD SUV"),

        # Minivans & MPVs
        ("Delica D:5", "All-Terrain 4WD Monocoque Minivan"),
        ("Delica D:2", "Compact Tall Wagon"),
        ("Delica D:3", "Compact Cargo Van"),
        ("Delica Mini", "Rugged 4WD Kei Crossover"),
        ("Delica Space Gear", "Off-road 4WD Minivan"),
        ("Delica Star Wagon", "Classic 4WD High-roof Van"),
        ("Grandis", "Stylish 7-seater MPV"),
        ("Chariot", "7-seater MPV"),
        ("Chariot Grandis", "Mid-size MPV"),
        ("Dion", "Compact 7-seater MPV"),
        ("Space Star", "Compact MPV / Hatchback"),

        # Trucks & Commercial
        ("Triton", "1-ton Mid-size Pickup (L200)"),
        ("Strada", "Classic Pickup Truck"),
        ("Canter", "Light Commercial Truck"),
        ("Canter Guts", "Light Cabover Truck"),
        ("Minicab Van", "Kei Commercial Microvan"),
        ("Minicab Truck", "Kei Commercial Microtruck"),
        ("Minicab MiEV", "Electric Commercial Kei Van"),

        # Sports Cars
        ("GTO", "Twin-Turbo AWD V6 Supercoupe (3000GT)"),
        ("FTO", "V6 FWD Sports Coupe"),
        ("Eclipse", "Sport Coupe"),
        ("Starion", "RWD Turbo Sports Coupe"),

        # Kei Cars
        ("eK Wagon", "Kei Tall Hatchback"),
        ("eK Custom", "Sporty Kei Hatchback"),
        ("eK Space", "Super Height Kei Wagon"),
        ("eK Space Custom", "Aero Super Height Kei Wagon"),
        ("eK X", "Crossover Styled Kei Hatchback"),
        ("eK X Space", "Crossover Super Height Kei Wagon"),
        ("eK X EV", "All-Electric Kei Car"),
        ("Town Box", "Kei Passenger Van"),
    ],

    "SUBARU": [
        # Compact / Hatchbacks
        ("Impreza", "AWD Compact Hatchback / Sedan"),
        ("Impreza Sport", "5-door Sport Hatchback"),
        ("Impreza G4", "4-door Sedan"),
        ("Impreza WRX", "Turbo Rally Sports Car"),
        ("Impreza WRX STI", "World Rally Icon (22B / S204 / RA)"),
        ("XV", "Crossover SUV (Crosstrek)"),
        ("XV Hybrid", "Hybrid Crossover"),
        ("Crosstrek", "All-Terrain Compact Crossover"),
        ("Justy", "Subcompact Tall Wagon"),
        ("Dex", "Subcompact Boxy Hatchback"),
        ("Trezia", "Compact Hatchback"),

        # Wagons & Tourers
        ("Levorg", "Sports Tourer Wagon"),
        ("Levorg Layback", "Elevated Crossover Tourer"),
        ("Legacy B4", "Mid-size AWD Sports Sedan"),
        ("Legacy Touring Wagon", "Pioneering Performance Wagon (GT-B)"),
        ("Legacy Outback", "All-Terrain Crossover Wagon"),
        ("Outback", "Flagship All-Terrain Crossover Wagon"),
        ("Exiga", "7-seater Touring MPV"),
        ("Exiga Crossover 7", "7-seater Crossover SUV"),

        # SUVs & 4WD
        ("Forester", "Mid-size AWD SUV"),
        ("Forester e-BOXER", "Hybrid AWD SUV"),
        ("Forester STI", "Turbo Performance SUV (SG9)"),
        ("Solterra", "All-Electric AWD SUV"),
        ("Ascent", "3-row Mid-size SUV"),
        ("Tribeca", "Mid-size 3-row Crossover"),

        # Sports Cars
        ("WRX S4", "AWD Performance Sports Sedan"),
        ("WRX STI", "EJ20/EJ25 AWD Rally Sedan"),
        ("BRZ", "Lightweight RWD Boxer Sports Coupe"),
        ("SVX", "Giugiaro-styled Luxury Grand Tourer (Alcyone SVX)"),
        ("Alcyone", "Classic Wedge Turbo Sports Coupe"),

        # Kei Cars
        ("Stella", "Tall Height Kei Wagon"),
        ("Stella Custom", "Aero Tall Height Kei Wagon"),
        ("Chiffon", "Super Height Kei Wagon"),
        ("Chiffon Custom", "Aero Super Height Kei Wagon"),
        ("Pleo", "Kei Hatchback"),
        ("Pleo Plus", "Ultra-efficient Kei Hatchback"),
        ("Lucra", "Tall Kei Wagon"),
        ("Lucra Custom", "Aero Tall Kei Wagon"),
        ("R1", "Compact 2-door City Coupe"),
        ("R2", "Curvaceous 5-door Kei Car"),
        ("Vivio", "Kei Hatchback (Supercharged RX-R)"),
        ("Vivio Bistro", "Retro-styled Kei Hatchback"),
        ("Sambar Van", "Rear-engine 'Porsche of Kei Vans'"),
        ("Sambar Truck", "Rear-engine Kei Microtruck"),
        ("Sambar Dias", "Passenger Trim Microvan"),
    ],

    "SUZUKI": [
        # Compact / Sedans
        ("Swift", "World-renowned Compact Hatchback"),
        ("Swift Sport", "Lightweight Performance Hot Hatch"),
        ("Baleno", "Spacious Compact Hatchback"),
        ("Ignis", "Compact Crossover Hatchback"),
        ("Splash", "Subcompact Urban Hatchback"),
        ("Cultus", "Classic Subcompact"),
        ("Celerio", "Entry Subcompact"),
        ("S-Presso", "Mini Urban Crossover"),
        ("Kizashi", "AWD Mid-size Executive Sedan"),
        ("SX4", "Compact Crossover Hatchback / Sedan"),
        ("SX4 S-Cross", "Subcompact Crossover SUV"),
        ("Ciaz", "Subcompact Sedan"),

        # SUVs & Crossovers
        ("Jimny", "Legendary Kei 4WD Off-Roader"),
        ("Jimny Sierra", "Wide-body Compact 4WD Off-Roader"),
        ("Escudo", "Compact 4WD SUV (Vitara / Grand Vitara)"),
        ("Vitara", "Compact Crossover SUV"),
        ("Grand Vitara", "Mid-size 4WD SUV"),
        ("Xbee", "Retro Crossover Kei-derived Wagon"),
        ("Fronx", "Coupe Crossover SUV"),

        # Minivans & MPVs
        ("Solio", "Compact Tall Wagon"),
        ("Solio Bandit", "Sporty Compact Tall Wagon"),
        ("Landy", "3-row Family Minivan"),
        ("Ertiga", "Compact 7-seater MPV"),
        ("APV", "Compact Commercial / Passenger MPV"),
        ("XL7", "7-seater Crossover MPV"),

        # Kei Cars
        ("Alto", "Ultra-efficient Iconic Kei Hatchback"),
        ("Alto Works", "Turbocharged Kei Pocket Rocket"),
        ("Alto Lapin", "Retro Cute Kei Car"),
        ("Alto Lapin LC", "Classic Vintage-styled Kei Car"),
        ("Alto Eco", "Eco-friendly Kei Car"),
        ("Wagon R", "Pioneering Tall Height Kei Wagon"),
        ("Wagon R Stingray", "Sporty Tall Height Kei Wagon"),
        ("Wagon R Smile", "Sliding-door Retro Kei Wagon"),
        ("Wagon R FX", "Standard Trim Kei Wagon"),
        ("Wagon R FZ", "Aero Trim Kei Wagon"),
        ("Spacia", "Super Height Kei Wagon"),
        ("Spacia Custom", "Aero Super Height Kei Wagon"),
        ("Spacia Gear", "SUV-styled Super Height Kei Wagon"),
        ("Spacia Base", "Multi-utility Lifestyle Kei Van"),
        ("Hustler", "Iconic Crossover Kei SUV"),
        ("Hustler Tough Wild", "Rugged Outdoor Crossover Kei"),
        ("Cappuccino", "Turbo RWD Kei Roadster (F6A/K6A)"),
        ("Twin", "Micro 2-seater Urban Car"),
        ("Cara", "Gullwing Mid-engine Kei Sports Car"),
        ("Kei", "Compact Kei Crossover"),
        ("Kei Works", "Sport Turbo Kei Car"),
        ("Cervo", "Sporty Kei Hatchback"),
        ("Palette", "Super Height Kei Wagon"),
        ("Palette SW", "Aero Super Height Kei Wagon"),
        ("Every", "Cabover Kei Microvan"),
        ("Every Wagon", "Passenger Comfort Kei Microvan"),
        ("Carry Truck", "Best-selling Kei Microtruck"),
        ("Super Carry", "Extended Cab Kei Microtruck"),
    ],

    "DAIHATSU": [
        # Compact / Hatchbacks
        ("Boon", "Subcompact Hatchback"),
        ("Boon CILQ", "Chic-styled Subcompact"),
        ("Boon Luminas", "7-seater Compact MPV"),
        ("Thor", "Compact Tall Sliding-door Wagon"),
        ("Thor Custom", "Aero Compact Tall Wagon"),
        ("Sirion", "Subcompact Hatchback"),
        ("YRV", "Turbo Compact Wagon"),
        ("Charade", "Classic Subcompact (De Tomaso / GTti)"),
        ("Storia", "Classic Compact"),
        ("Applause", "Compact Sedan with Hatch"),
        ("Altis", "Executive Sedan (Camry OEM)"),
        ("Mebius", "Hybrid Wagon (Prius Alpha OEM)"),

        # SUVs & Crossovers
        ("Rocky", "Compact Crossover SUV (Best-seller)"),
        ("Rocky e-SMART Hybrid", "Series Hybrid Crossover"),
        ("Taft", "Rugged Glass-roof Kei Crossover"),
        ("Terios", "Mini 4WD SUV"),
        ("Terios Kid", "Kei 4WD Mini-SUV"),
        ("Terios Lucia", "City Kei SUV"),
        ("Be-go", "Compact 4WD SUV"),

        # Sports Cars
        ("Copen", "Retractable Hardtop Kei Roadster"),
        ("Copen Robe", "Modern Sport Kei Roadster"),
        ("Copen Cero", "Round-headlight Classic Kei Roadster"),
        ("Copen XPLAY", "Crossover Kei Roadster"),
        ("Copen GR Sport", "Gazoo Racing Tuned Kei Roadster"),

        # Kei Cars
        ("Tanto", "Revolutionary Miracle-open Door Kei Wagon"),
        ("Tanto Custom", "Aero Super Height Kei Wagon"),
        ("Tanto FunCross", "Outdoor-oriented Kei Wagon"),
        ("Tanto Exe", "Premium Super Height Kei Wagon"),
        ("Tanto Exe Custom", "Aero Super Height Kei Wagon"),
        ("Move", "Flagship Tall Height Kei Wagon"),
        ("Move Custom", "Aero Tall Height Kei Wagon"),
        ("Move Canbus", "Retro Sliding-door Lifestyle Kei Wagon"),
        ("Move Conte", "Boxy Styled Kei Wagon"),
        ("Move Conte Custom", "Aero Boxy Kei Wagon"),
        ("Move Latte", "Cute Rounded Kei Wagon"),
        ("Mira", "Historic Mainstay Kei Hatchback"),
        ("Mira e:S", "High Efficiency Eco Kei Hatchback"),
        ("Mira Tocot", "Easy-driving Square Kei Car"),
        ("Mira Gino", "Mini-inspired Classic Retro Kei Car"),
        ("Mira Cocoa", "Fashionable Female-oriented Kei Car"),
        ("Mira Custom", "Sporty Trim Kei Hatchback"),
        ("Mira TR-XX", "Turbo AWD Classic Hot Hatch"),
        ("Cast Style", "Refined Classic Kei Crossover"),
        ("Cast Activa", "SUV-themed Kei Crossover"),
        ("Cast Sport", "Sport-tuned Kei Hatchback"),
        ("Wake", "Ultra-high Ceiling Activity Kei Wagon"),
        ("Atrai", "Passenger Luxury Kei Microvan"),
        ("Atrai Wagon", "Lifestyle Kei Microvan"),
        ("Atrai 7", "7-seater Extended Kei MPV"),
        ("Hijet Cargo", "Number-one Commercial Kei Microvan"),
        ("Hijet Truck", "Heavy-duty Kei Microtruck"),
        ("Hijet Deck Van", "4-door Pickup Hybrid Microvan"),
        ("Hijet Caddie", "2-seater Commercial Kei Van"),
        ("Esse", "Lightweight Fun Kei Hatchback"),
        ("Naked", "Rugged Industrial-styled Kei Car"),
        ("Opti", "Sedan-styled 4-door Kei Car"),
        ("Sonica", "Low-roof Long-distance Touring Kei Car"),
        ("Max", "Sporty Tall Kei Car"),
    ],

    "LEXUS": [
        # Sedans & Hatchbacks
        ("LS500", "Flagship Twin-Turbo V6 Executive Sedan"),
        ("LS500h", "Flagship Hybrid Executive Sedan"),
        ("LS460", "Flagship V8 Executive Sedan"),
        ("LS600h", "Flagship V8 Hybrid Executive Sedan"),
        ("LS430", "Classic Ultra-Reliable V8 Sedan"),
        ("LS400", "Pioneering Luxury Flagship V8"),
        ("GS350", "Performance Mid-size Luxury Sedan"),
        ("GS450h", "Hybrid Performance Mid-size Sedan"),
        ("GS300", "Mid-size Luxury Sedan"),
        ("GS F", "Naturally Aspirated 5.0L V8 Sports Sedan"),
        ("ES300h", "Executive Luxury Hybrid Sedan"),
        ("ES350", "Executive Luxury V6 Sedan"),
        ("IS300h", "Compact Executive Hybrid Sports Sedan"),
        ("IS350", "Compact Executive V6 Sports Sedan"),
        ("IS300", "Turbo Compact Sports Sedan"),
        ("IS250", "Compact Executive Sports Sedan"),
        ("IS F", "V8 Performance Sports Sedan"),
        ("IS500", "5.0L V8 F Sport Performance Sedan"),
        ("HS250h", "Dedicated Luxury Hybrid Sedan"),
        ("CT200h", "Premium Compact Hybrid Hatchback"),

        # Coupes & Convertibles
        ("LC500", "Flagship V8 Luxury Grand Tourer Coupe"),
        ("LC500h", "Flagship Multi-stage Hybrid Coupe"),
        ("LC500 Convertible", "V8 Luxury Convertible"),
        ("RC350", "V6 Luxury Sports Coupe"),
        ("RC300h", "Hybrid Luxury Sports Coupe"),
        ("RC F", "5.0L V8 Track-focused Sports Coupe"),
        ("SC430", "V8 Hardtop Luxury Convertible"),
        ("LFA", "V10 Halo Supercar (500 units worldwide)"),

        # SUVs & Crossovers
        ("LX600", "Flagship Luxury Full-size Twin-Turbo 4WD"),
        ("LX570", "Flagship Luxury Full-size V8 4WD"),
        ("LX470", "Flagship Luxury Classic V8 4WD"),
        ("GX550", "Luxury All-Terrain Twin-Turbo SUV"),
        ("GX460", "Luxury All-Terrain V8 SUV"),
        ("GX470", "Classic Luxury All-Terrain V8 SUV"),
        ("RX500h", "Performance Hybrid Luxury Crossover"),
        ("RX450h+", "Plug-in Hybrid Luxury Crossover"),
        ("RX450h", "Hybrid Mid-size Luxury Crossover"),
        ("RX350h", "Hybrid Mid-size Luxury Crossover"),
        ("RX350", "Mid-size Luxury Crossover"),
        ("RX300", "Turbo Mid-size Luxury Crossover"),
        ("NX450h+", "Plug-in Hybrid Compact Luxury SUV"),
        ("NX350h", "Hybrid Compact Luxury SUV"),
        ("NX350", "Turbo AWD Compact Luxury SUV"),
        ("NX250", "Compact Luxury SUV"),
        ("NX300h", "Hybrid Compact Luxury SUV"),
        ("UX250h", "Subcompact Luxury Hybrid Crossover"),
        ("UX300h", "Subcompact Luxury Hybrid Crossover"),
        ("UX300e", "All-Electric Luxury Subcompact Crossover"),
        ("UX200", "Subcompact Luxury Crossover"),
        ("TX350", "3-row Mid-size Luxury SUV"),
        ("TX500h", "3-row Performance Hybrid SUV"),
        ("RZ450e", "Dedicated All-Electric Luxury SUV"),
        ("RZ300e", "Dedicated All-Electric FWD Luxury SUV"),
        ("LBX", "Premium Subcompact Luxury Crossover"),

        # Luxury MPVs
        ("LM500h", "Ultra-Luxury Flagship Hybrid MPV"),
        ("LM350h", "Ultra-Luxury Flagship Hybrid MPV"),
        ("LM300h", "Ultra-Luxury Executive MPV"),
    ],

    "ISUZU": [
        # Commercial Trucks & Buses
        ("Elf", "Light Commercial Truck (World Standard)"),
        ("Elf Truck", "Light Cabover Work Truck"),
        ("Forward", "Medium-Duty Commercial Truck"),
        ("Giga", "Heavy-Duty Commercial Truck"),
        ("Como", "Commercial Passenger / Cargo Van"),
        ("Fargo", "Classic Commercial Van"),
        ("Journey", "Light Bus"),
        ("Erga", "Heavy-Duty Transit Bus"),
        ("Gala", "Luxury Highway Coach Bus"),

        # Pickups & SUVs
        ("D-Max", "Rugged 1-ton Mid-size Pickup Truck"),
        ("MU-X", "3-row All-Terrain 4WD SUV"),
        ("Bighorn", "Rugged 4WD SUV (Trooper)"),
        ("Trooper", "Classic All-Terrain 4WD"),
        ("MU", "2-door Sport Utility 4WD"),
        ("Wizard", "5-door 4WD SUV"),
        ("VehiCROSS", "Futuristic All-Terrain 4WD Homologation"),
        ("Rodeo", "Compact / Mid-size Pickup"),

        # Historic Passenger Cars
        ("Gemini", "Sport Compact Sedan / Coupe"),
        ("Piazza", "Giugiaro-styled Turbo RWD Coupe"),
        ("Aska", "Mid-size Sedan"),
        ("Bellett", "Classic 1960s GT Sports Sedan"),
        ("117 Coupe", "Classic Handcrafted Italian-styled Coupe"),
    ],

    "HINO": [
        ("Dutro", "Light Commercial Truck"),
        ("Ranger", "Medium-Duty Commercial Truck"),
        ("Profia", "Heavy-Duty Flagship Commercial Truck"),
        ("Liesse", "Light Commercial Bus"),
        ("Poncho", "Low-floor Community Bus"),
        ("Rainbow", "Medium Commercial Bus"),
        ("Melpha", "Medium Touring Coach"),
        ("Blue Ribbon", "Heavy Transit City Bus"),
        ("S'elega", "Luxury Highway Tourist Coach"),
        ("Contessa", "Classic Rear-engine Sedan / Coupe"),
    ],

    "MITSUOKA": [
        ("Orochi", "Mid-engine Supercar (V6 3.3L)"),
        ("Viewt", "Jaguar Mk II Styled Classic Compact"),
        ("Buddy", "Classic American SUV Styled Crossover"),
        ("Rock Star", "Corvette C2 Styled Roadster (Miata base)"),
        ("Ryugi", "Classic British Styled Compact Sedan / Wagon"),
        ("Galue", "Rolls-Royce Styled Luxury Executive Sedan"),
        ("Himiko", "Morgan Styled Classic Luxury Roadster"),
        ("Like", "Electric City Microcar"),
        ("Nouera", "Classic Styled Executive Sedan"),
        ("Ray", "Classic Mini Styled Kei Car"),
        ("Ryoga", "Classic British Styled Mid-size Sedan"),
        ("Zero1", "Lotus Seven Styled Lightweight Sports Car"),
        ("Le-Seyde", "Art Deco Styled Grand Luxury Coupe"),
    ]
}


def normalize_str(s):
    if not s:
        return ""
    # strip leading style descriptors like "Sedan ", "SUV ", etc.
    cleaned = re.sub(
        r'^(Sedan|SUV|Hatchback|Coupe|Convertible|Electric|Commercial|Minivan|Compact Car|Kei Car|Sports|Car)\s+',
        '',
        s,
        flags=re.I
    )
    cleaned = re.sub(r'\s*\([^)]*\)', '', cleaned)
    return re.sub(r'[^a-zA-Z0-9]', '', cleaned).lower()


class Command(BaseCommand):
    help = "Populate Japanese auto auctions and car models into the database, skipping any existing entries."

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            default=None,
            help='Populate for a specific user ID only. If omitted, populates for all users.'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        if user_id:
            users = User.objects.filter(id=user_id)
            if not users.exists():
                self.stdout.write(self.style.ERROR(f"User with ID {user_id} not found."))
                return
        else:
            users = User.objects.all()
            if not users.exists():
                self.stdout.write(self.style.ERROR("No users found in the system."))
                return

        self.stdout.write(self.style.SUCCESS(
            f"Starting data population for {users.count()} user(s)..."
        ))

        total_auctions_created = 0
        total_auctions_skipped = 0
        total_cars_created = 0
        total_cars_skipped = 0

        for user in users:
            self.stdout.write(self.style.NOTICE(f"\nProcessing User ID {user.id} ({user.email})..."))

            # --- 1. AUCTIONS ---
            existing_auctions = list(Auction.objects.filter(user=user).values('id', 'name', 'auction_type'))
            existing_names_lower = {a['name'].strip().lower() for a in existing_auctions}

            user_auctions_created = 0
            user_auctions_skipped = 0

            with transaction.atomic():
                for name, auction_type, venue_key, description in JAPAN_AUCTIONS:
                    name_clean = name.strip()
                    name_lower = name_clean.lower()

                    # Check if exact name exists or venue key is covered
                    is_existing = False
                    if name_lower in existing_names_lower:
                        is_existing = True
                    else:
                        for exist_name in existing_names_lower:
                            if venue_key and venue_key in exist_name:
                                is_existing = True
                                break

                    if is_existing:
                        user_auctions_skipped += 1
                    else:
                        Auction.objects.create(
                            name=name_clean,
                            auction_type=auction_type,
                            description=description,
                            user=user
                        )
                        existing_names_lower.add(name_lower)
                        user_auctions_created += 1

            self.stdout.write(f"  Auctions -> Created: {user_auctions_created}, Skipped: {user_auctions_skipped}")
            total_auctions_created += user_auctions_created
            total_auctions_skipped += user_auctions_skipped

            # --- 2. CAR CATEGORIES (MAKER & MODEL) ---
            existing_categories = list(CarCategory.objects.filter(user=user).values('id', 'company', 'model'))
            existing_cat_keys = {
                (c['company'].strip().upper(), normalize_str(c['model'])): c['id']
                for c in existing_categories
            }
            existing_cat_exact = {
                (c['company'].strip().upper(), c['model'].strip().lower()): c['id']
                for c in existing_categories
            }

            user_cars_created = 0
            user_cars_skipped = 0

            with transaction.atomic():
                for company, models in JAPAN_CARS.items():
                    comp_upper = company.strip().upper()
                    for model_name, description in models:
                        model_clean = model_name.strip()
                        norm_m = normalize_str(model_clean)
                        exact_key = (comp_upper, model_clean.lower())
                        norm_key = (comp_upper, norm_m)

                        if exact_key in existing_cat_exact or norm_key in existing_cat_keys:
                            user_cars_skipped += 1
                        else:
                            CarCategory.objects.create(
                                company=comp_upper,
                                model=model_clean,
                                description=description,
                                user=user
                            )
                            existing_cat_keys[norm_key] = True
                            existing_cat_exact[exact_key] = True
                            user_cars_created += 1

            self.stdout.write(f"  Car Categories -> Created: {user_cars_created}, Skipped: {user_cars_skipped}")
            total_cars_created += user_cars_created
            total_cars_skipped += user_cars_skipped

        self.stdout.write(self.style.SUCCESS(
            f"\nData population complete!"
            f"\nTotal Auctions: {total_auctions_created} created, {total_auctions_skipped} skipped."
            f"\nTotal Car Categories: {total_cars_created} created, {total_cars_skipped} skipped."
        ))
