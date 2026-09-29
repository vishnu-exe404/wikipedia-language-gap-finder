"""Regenerates the tiny demo dataset in the Wikimedia structured schema."""
import json, os

def art(qid, lang, name, abstract, sections, fields, image=True):
    secs = [{"type": "section", "name": "Abstract", "has_parts": [{"type": "paragraph", "value": abstract}]}]
    for title, text in sections:
        secs.append({"type": "section", "name": title, "has_parts": [{"type": "paragraph", "value": text}]})
    info = [{"type": "infobox", "name": "Infobox", "has_parts": [{"type": "section", "name": "", "has_parts": [
        {"type": "field", "name": f, "value": v} for f, v in fields]}]}]
    d = {"name": name, "url": f"https://{lang}.wikipedia.org/wiki/{name}", "abstract": abstract,
         "main_entity": {"identifier": qid}, "sections": secs, "infoboxes": info}
    if image:
        d["image"] = {"content_url": "https://example.org/x.jpg"}
    return d

lorem = "This section describes the topic in some detail with several words of text. " * 6
hlorem = "यह खंड विषय के बारे में कुछ जानकारी देता है। " * 3

en = [
 art("DEMO1", "en", "Prayagraj", "Prayagraj, formerly Allahabad, is a major city in Uttar Pradesh at the confluence of the Ganges and Yamuna. " * 3,
     [("History", lorem), ("Geography", lorem), ("Climate", lorem), ("Demographics", lorem), ("Economy", lorem), ("Culture", lorem), ("Transport", lorem), ("Education", lorem)],
     [("Country", "India"), ("State", "Uttar Pradesh"), ("Area", "365 km2"), ("Population", "1.1 million"), ("Elevation", "98 m"), ("Postal code", "211001")]),
 art("DEMO2", "en", "Taj Mahal", "The Taj Mahal is an ivory-white marble mausoleum in Agra built by Shah Jahan. " * 3,
     [("History", lorem), ("Architecture", lorem), ("Gardens", lorem), ("Conservation", lorem), ("Tourism", lorem)],
     [("Location", "Agra"), ("Built", "1632-1653"), ("Architect", "Ustad Ahmad Lahauri"), ("Style", "Mughal")]),
 art("DEMO3", "en", "Kumbh Mela", "The Kumbh Mela is a major pilgrimage and festival in Hinduism held at four river sites. " * 3,
     [("Origin", lorem), ("Locations", lorem), ("Rituals", lorem), ("Attendance", lorem), ("Safety and management", lorem), ("UNESCO recognition", lorem)],
     [("Frequency", "Every 12 years"), ("Venues", "Four"), ("Type", "Pilgrimage")]),
]
hi = [
 art("DEMO1", "hi", "प्रयागराज", "प्रयागराज उत्तर प्रदेश का एक प्रमुख शहर है। ", [("इतिहास", hlorem), ("भूगोल", hlorem), ("संस्कृति", hlorem)],
     [("देश", "भारत"), ("राज्य", "उत्तर प्रदेश")], image=True),
 art("DEMO2", "hi", "ताजमहल", "ताजमहल आगरा में स्थित संगमरमर का मकबरा है जिसे शाहजहाँ ने बनवाया। " * 2,
     [("इतिहास", hlorem), ("वास्तुकला", hlorem), ("उद्यान", hlorem), ("पर्यटन", hlorem)],
     [("स्थान", "आगरा"), ("निर्माण", "1632-1653"), ("शैली", "मुगल")]),
 art("DEMO3", "hi", "कुम्भ मेला", "कुम्भ मेला हिन्दू धर्म का एक बड़ा धार्मिक मेला है। ", [("उत्पत्ति", hlorem)],
     [("आवृत्ति", "हर 12 वर्ष")], image=False),
]
here = os.path.join(os.path.dirname(__file__), "..", "sample_data")
for name, rows in (("en_sample.jsonl", en), ("hi_sample.jsonl", hi)):
    with open(os.path.join(here, name), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
