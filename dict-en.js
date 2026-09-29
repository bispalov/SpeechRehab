// Словарь и пары «похожих слов» — английский.
const dictionaryEn = {
    "1. Household & Furniture": ["House", "Bed", "Ta-ble", "Chair", "Clos-et", "So-fa", "Arm-chair", "Win-dow", "Door", "Mir-ror", "Shelf", "Car-pet", "Lamp", "Pil-low", "Blan-ket", "Sheet", "Tel-e-vi-sion", "Clock", "Key", "Lock", "Wall", "Floor", "Ceil-ing", "Bal-co-ny", "Cur-tain", "Ra-di-a-tor", "Chan-de-lier", "Vase", "Pic-ture", "Cur-tain rod", "Hang-er", "Night-stand", "Mat-tress", "Plaid", "Ta-ble-cloth", "Blinds", "Draw-er", "Thresh-old", "Han-dle", "Sock-et"],
    "2. Dishes & Kitchen": ["Spoon", "Fork", "Knife", "Plate", "Cup", "Glass", "Pot", "Fry-ing pan", "Ket-tle", "Pitch-er", "Bowl", "Sau-cer", "La-dle", "Spat-u-la", "Grat-er", "Cut-ting board", "Tray", "Salt sha-ker", "Su-gar bowl", "But-ter dish", "Bread box", "Ov-en", "Stove", "Re-frig-er-a-tor", "Mi-cro-wave", "Mix-er", "Blen-der", "Fil-ter", "Sponge", "Tow-el", "Sink", "Fau-cet", "Roll-ing pin", "Sieve", "Col-an-der", "Jar", "Bot-tle", "Cork", "Foil", "Parch-ment"],
    "3. Health & Body": ["Doc-tor", "Hos-pi-tal", "Phar-ma-cy", "Med-i-cine", "Pill", "Ther-mom-e-ter", "In-jec-tion", "Ban-dage", "Cot-ton wool", "Patch", "Oint-ment", "Drops", "Pain", "Heart", "Head", "Arm", "Leg", "Fin-ger", "Back", "Stom-ach", "Chest", "Neck", "Face", "Eye", "Ear", "Nose", "Mouth", "Tooth", "Tongue", "Knee", "El-bow", "Shoul-der", "Blood", "Pulse", "Pres-sure", "Tem-per-a-ture", "Cough", "Run-ny nose", "Sleep"],
    "4. Communication & Emotions": ["Hel-lo", "Thank you", "Please", "Yes", "No", "Good", "Bad", "Help me", "How are you", "Good-bye", "Wel-come", "Sor-ry", "Love", "Joy", "Sad-ness", "Smile", "Laugh-ter", "Tears", "Kind-ness", "Peace", "Friend-ship", "Care", "Ten-der-ness", "Kiss", "Hug", "Calm", "Fear", "Sur-prise", "Hope", "Faith", "A-gree", "Don't want", "Will", "Won't", "Give", "Here", "Go", "Stop", "Lis-ten", "Look"],
    "5. Clothes & Shoes": ["Shirt", "Pants", "Jeans", "Dress", "Skirt", "T-shirt", "Sweat-er", "Car-di-gan", "Jack-et", "Coat", "Rain-coat", "Hat", "Scarf", "Gloves", "Mit-tens", "Socks", "Tights", "Un-der-wear", "Pa-ja-mas", "Robe", "Boots", "Shoes", "Sneak-ers", "Slip-pers", "San-dals", "Belt", "But-ton", "Zip-per", "Pock-et", "Col-lar", "Sleeve", "Hood", "Shoe-la-ces", "Cap", "Vest", "Suit"],
    "6. Food & Grocery": ["Bread", "But-ter", "Cheese", "Milk", "Meat", "Fish", "Egg", "Soup", "Por-ridge", "Sal-ad", "Salt", "Su-gar", "Pep-per", "Sauce", "Pas-ta", "Ce-re-al", "Rice", "Buck-wheat", "Noo-dles", "Pie", "Cake", "Cook-ie", "Can-dy", "Choc-o-late", "Hon-ey", "Jam", "Sour cream", "Cot-tage cheese", "Ke-fir", "Yo-gurt", "Sau-sage", "Sau-sa-ges", "Cut-let", "Dump-lings", "Pan-cakes", "Sand-wich", "Flour", "Yeast", "Vin-e-gar", "Mus-tard"],
    "7. Drinks": ["Wa-ter", "Tea", "Cof-fee", "Juice", "Milk", "Com-pote", "Fruit drink", "Jel-ly", "Lem-on-ade", "Kvass", "Cock-tail", "Co-coa", "Min-er-al wa-ter", "De-coc-tion", "Drink", "Nec-tar", "Es-pres-so", "Cap-puc-ci-no", "Smooth-ie", "Ton-ic"],
    "8. Fruits & Berries": ["Ap-ple", "Pear", "Ba-nan-a", "Or-ange", "Lem-on", "Tan-ger-ine", "Peach", "A-pri-cot", "Plum", "Grapes", "Straw-ber-ry", "Rasp-ber-ry", "Wild straw-ber-ry", "Cher-ry", "Sweet cher-ry", "Blue-ber-ry", "Cur-rant", "Wa-ter-mel-on", "Mel-on", "Pine-ap-ple", "Ki-wi", "Man-go", "Pome-gran-ate", "Fig", "Per-sim-mon", "Cher-ry plum", "Black-ber-ry", "Cran-ber-ry", "Lin-gon-ber-ry", "Sea buck-thorn"],
    "9. Vegetables & Greens": ["Po-ta-to", "Car-rot", "Beet-root", "On-ion", "Gar-lic", "Cu-cum-ber", "To-ma-to", "Cab-bage", "Pep-per", "Zuc-chi-ni", "Egg-plant", "Pump-kin", "Peas", "Beans", "Corn", "Rad-ish", "Tur-nip", "Greens", "Dill", "Pars-ley", "Sal-ad", "Spin-ach", "Sor-rel", "Cel-e-ry", "Ba-sil"],
    "10. Hygiene & Personal Care": ["Soap", "Sham-poo", "Tooth-paste", "Brush", "Wa-ter", "Tow-el", "Comb", "Scis-sors", "Mir-ror", "Cream", "Nap-kin", "Pa-per", "Wash-cloth", "Foam", "Gel", "Per-fume", "De-od-o-rant", "Ra-zor", "Cot-ton wool", "Pum-ice"],
    "11. Family & People": ["Mom", "Dad", "Son", "Daugh-ter", "Grand-moth-er", "Grand-fa-ther", "Broth-er", "Sis-ter", "Grand-son", "Grand-daugh-ter", "Un-cle", "Aunt", "Hus-band", "Wife", "Child", "Friend", "Neigh-bor", "Guest", "Per-son", "Ba-by"],
    "12. Professions": ["Doc-tor", "Teach-er", "Cook", "Driv-er", "Sell-er", "Build-er", "Fire-fight-er", "Po-lice of-fi-cer", "Post-man", "Hair-dress-er", "Seam-stress", "Plumb-er", "E-lec-tri-cian", "En-gi-neer", "Pi-lot"],
    "13. City & Transport": ["Cit-y", "Street", "House", "Road", "Car", "Bus", "Tram", "Trol-ley-bus", "Sub-way", "Train", "Air-plane", "Tax-i", "Bus stop", "Store", "Park", "Phar-ma-cy", "Bridge", "Traf-fic light", "Side-walk", "Square"],
    "14. Nature & Weather": ["Sun", "Sky", "Cloud", "Rain", "Snow", "Wind", "Thun-der-storm", "Rain-bow", "Star", "Moon", "Day", "Night", "Morn-ing", "Eve-ning", "For-est", "Riv-er", "Lake", "Sea", "Moun-tain", "Field"],
    "15. Time & Calendar": ["Time", "Hour", "Min-ute", "Sec-ond", "Day", "Week", "Month", "Year", "Yes-ter-day", "To-day", "To-mor-row", "Mon-day", "Tues-day", "Wednes-day", "Thurs-day", "Fri-day", "Sat-ur-day", "Sun-day", "Win-ter", "Spring", "Sum-mer", "Au-tumn"],
    "16. Domestic Animals": ["Cat", "Dog", "Cow", "Horse", "Pig", "Sheep", "Goat", "Rab-bit", "Pup-py", "Kit-ten", "Calf", "Foal", "Don-key", "Ham-ster"],
    "17. Wild Animals": ["Wolf", "Fox", "Bear", "Hare", "Hedge-hog", "Squir-rel", "Deer", "Elk", "Lion", "Ti-ger", "El-e-phant", "Mon-key", "Gi-raffe", "Hip-po", "Croc-o-dile"],
    "18. Birds": ["Bird", "Spar-row", "Crow", "Pig-eon", "Tit", "Wood-peck-er", "Duck", "Goose", "Chick-en", "Roost-er", "Tur-key", "Owl", "Ea-gle", "Stork", "Swal-low"],
    "19. Colors": ["White", "Black", "Red", "Blue", "Green", "Yel-low", "Or-ange", "Pur-ple", "Pink", "Brown", "Gray", "Light blue", "Beige", "Bur-gun-dy", "Lime"],
    "20. Numbers & Counting": ["One", "Two", "Three", "Four", "Five", "Six", "Sev-en", "Eight", "Nine", "Ten", "Hun-dred", "Thou-sand", "First", "Sec-ond", "Third", "Ma-ny", "Few", "Half", "Ze-ro", "Pair"],
    "21. Actions (Verbs)": ["Walk", "Sit", "Stand", "Lie", "Eat", "Drink", "Speak", "Read", "Write", "Take", "Wash", "Clean", "Dress", "Re-move", "O-pen", "Close"],
    "22. Qualities (Adjectives)": ["Big", "Small", "Hot", "Cold", "Warm", "Tas-ty", "Dirty", "New", "Old", "Kind", "Fast", "Slow", "Strong", "Light", "Dark", "Soft", "Hard"],
    "23. Tools & Repair": ["Ham-mer", "Nail", "Screw", "Screw-dri-ver", "Saw", "Pli-ers", "Axe", "Shov-el", "Rake", "Buck-et", "Brush", "Glue", "Paint", "Wire"],
    "24. Rest & Hobbies": ["Book", "News-pa-per", "Mu-sic", "Song", "Dance", "Cin-e-ma", "Ra-di-o", "Game", "Ball", "Gar-den", "Flow-ers", "Fish-ing", "Sport", "Hol-i-day"],
    "25. Stationery & Learning": ["Pen", "Pen-cil", "Note-book", "Note-pad", "Pa-per", "E-ras-er", "Rul-er", "Book", "Bag", "En-ve-lope", "Fold-er", "Glue", "Scis-sors", "Mar-ker", "Paints"]
};

const realWordPairsEn = {
    "House": ["Mouse", "Horse", "Blouse", "Hose", "Spouse"],
    "Chair": ["Hair", "Pair", "Bear", "Stair", "Fair"],
    "Cat": ["Hat", "Bat", "Rat", "Mat", "Cap"],
    "Dog": ["Log", "Fog", "Frog", "Dig", "Dot"],
    "Sun": ["Fun", "Run", "Gun", "Son", "Bun"],
    "Bed": ["Red", "Bad", "Beg", "Bell", "Bet"],
    "Pen": ["Pin", "Pan", "Pet", "Peg", "Ten"],
    "Book": ["Look", "Cook", "Hook", "Boot", "Box"]
};
