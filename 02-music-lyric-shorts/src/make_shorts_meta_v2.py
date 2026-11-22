"""Метаданные и график Shorts v2 World Metal Empire.

Использование: python make_shorts_meta_v2.py <out.md> <out.json>
Заголовки — хуки без названий франшизы (Warhammer / 40k / Emperor / Istvaan / Templar / Terra).
График: 3 в день — 12:00, 16:00, 19:00 МСК, с 23.11.2026.
"""
import json, sys
from datetime import date, timedelta

FULL = {  # трек -> id полного видео на канале
    "Eternal War": "jVF4Bd5hf58", "Angels of Death": "SuPWEtXs6VI", "Winter's Gate": "4RIkiHsnZVc",
    "Blood for the Red Angel": "lNd3SyeFPlg", "Ghosts of Istvaan": "zn1HjnGAZrE",
    "The last Black Templar": "LQFQS7dd9nk", "Children of the Void": "SB-V-fT3D4k",
    "Machine God Rising": "qDKbA_LKlc0", "The Siege of Terra": "zrQQxds13no",
    "When the Stars remember US": "8UY25HMrsJw", "The Rose in the Ashes": "KPYAgghEaCU",
    "Green Tide Rising": "8YL-SxKH_wQ",
}
DISC = ("⚙️ AI DISCLOSURE: music and vocals produced with the assistance of AI tools (Suno). "
        "Lyrics, visuals, editing and creative direction are original work of this channel.")
STREAM = "🎧 Listen on Yandex Music / VK Music / YouTube Music — coming soon"
SLOGAN = "Every world deserves an anthem."
TAGS_BASE = ["epic metal", "symphonic metal", "power metal", "metal shorts", "war metal", "epic music",
             "gaming music", "workout music", "battle music", "world metal empire"]

# id, трек, заголовок, история (1–2 строки), вопрос для закрепа, хэштеги
S = [
 ("WME_V01_eternal_war_chorus", "Eternal War", "What would you still die for? 🔥 Epic War Metal",
  "A war older than memory. An army that marches anyway — because someone has to hold the line.",
  "If the last star went dark tonight — would you still march?", "#epicmetal #powermetal #warmetal"),
 ("WME_V02_eternal_war_bridge", "Eternal War", "If the gods laugh at you — laugh back 💀 Heavy Metal",
  "Drums made of bones, a world burned to its final wall — and soldiers who answer the heavens with laughter.",
  "Duty, faith or wrath — which one keeps you standing?", "#heavymetal #thrashmetal #epicmetal"),
 ("WME_V03_eternal_war_final", "Eternal War", "POV: you are the last wall ⚔️ Epic Metal",
  "Everyone behind you is counting on one thing: that you don't step back.",
  "What's the one thing you'd never step back from?", "#epicmetal #powermetal #warmetal"),
 ("WME_V04_angels_chorus", "Angels of Death", "The sky opens. They descend. 🪽 Melodic Metalcore",
  "Fire falls from the clouds — and where mortal courage ends, they begin.",
  "Would you want them on your side — or never see them at all?", "#metalcore #epicmetal #metal"),
 ("WME_V05_angels_breakdown", "Angels of Death", "No fear. No pain. No doubt. 🔥 Metalcore Breakdown",
  "Made by fire, by blade, by blood. This is the moment the warriors stop being human.",
  "Which word hits harder: fear, pain or doubt?", "#metalcore #breakdown #metal"),
 ("WME_V06_angels_final", "Angels of Death", "Who answers the last call? ⚔️ Epic Metal",
  "When mankind stands at the edge of night, someone still has to answer.",
  "Who would you call at the edge of the night?", "#epicmetal #metalcore #metal"),
 ("WME_V07_ghosts_chorus", "Ghosts of Istvaan", "What is a sword when honor lies? 🗡️ Dark Metal",
  "Betrayed by their own brothers under a burning dawn — and still they refuse to die alone.",
  "What hurts more: an enemy's blade or a brother's?", "#darkmetal #melodicmetal #epicmetal"),
 ("WME_V08_ghosts_final", "Ghosts of Istvaan", "The oath remains when flesh is gone 👻 Dark Metal",
  "Their names were carved in flame and stone. Their oath outlived them.",
  "What promise would you keep even after death?", "#darkmetal #epicmetal #metal"),
 ("WME_V09_rose_chorus", "The Rose in the Ashes", "Who would you cross the stars for? 🥀 Symphonic Metal",
  "A soldier finds a single rose by a ruined chapel — and a name carved in stone.",
  "Who is your rose in the ashes?", "#symphonicmetal #metalballad #femalevocals"),
 ("WME_V10_rose_bridge", "The Rose in the Ashes", "One last dream of peace 🕊️ Symphonic Metal Ballad",
  "Maybe there is no peaceful dawn. But in your eyes, one last dream still holds on.",
  "Do you still believe the war ends someday?", "#symphonicmetal #metalballad #operametal"),
 ("WME_V11_rose_final", "The Rose in the Ashes", "Love that outlives the war 🥀 Symphonic Metal",
  "When the universe collapses, one promise remains: I will still come back to you.",
  "Can love really live beyond the stars?", "#symphonicmetal #metalballad #femalevocals"),
 ("WME_V12_siege_chorus", "The Siege of Terra", "If this wall falls, we all fall 🏰 Symphonic Metal",
  "The last palace. The last door. Every son of mankind waits his turn.",
  "Would you stand at the final gate?", "#symphonicmetal #epicmetal #powermetal"),
 ("WME_V13_siege_bridge", "The Siege of Terra", "Do not kneel before your fate 👑 Epic Metal",
  "Do not weep for the broken gate. If the throne is bought with pain, let the sacrifice remain.",
  "Is a throne worth what it costs?", "#epicmetal #symphonicmetal #metal"),
 ("WME_V14_siege_final", "The Siege of Terra", "The last hour of mankind 🔥 Epic Symphonic Metal",
  "The war drums rise. If the palace stands through darkness, mankind never dies.",
  "Would you rather fall with the palace or survive without it?", "#epicmetal #symphonicmetal #powermetal"),
 ("WME_V15_templar_chorus", "The last Black Templar", "Every brother fell. He kept going. ⚔️ Heavy Metal",
  "No rest, no home, no crown — one knight left, and the crusade still burns.",
  "Could you keep going if every brother fell?", "#heavymetal #powermetal #epicmetal"),
 ("WME_V16_templar_bridge", "The last Black Templar", "Kneel to no shadow 🛡️ Crusader Metal",
  "Bow to no throne. If I must die, I die alone — but the crusade goes on.",
  "What would you never kneel to?", "#heavymetal #epicmetal #metal"),
 ("WME_V17_templar_final", "The last Black Templar", "If I must die, I die alone ✝️ Epic Heavy Metal",
  "The oath becomes the scar. He will fight until the darkness burns beneath the stars.",
  "Is dying alone for a cause brave or tragic?", "#heavymetal #powermetal #epicmetal"),
 ("WME_V18_winter_chorus", "Winter's Gate", "Raise the horn. Wake the wolves. 🐺 Power Metal",
  "Snow on the armor, frost in the beard — and a pack that never turns its back.",
  "Wolf or lion — which would you follow into the storm?", "#powermetal #vikingmetal #epicmetal"),
 ("WME_V19_winter_bridge", "Winter's Gate", "Bury us deep. We hunt again. ❄️ Northern Power Metal",
  "No grave can hold what the sagas keep. The wolves still hunt while the gods sleep.",
  "What would you want your saga to say about you?", "#powermetal #vikingmetal #metal"),
 ("WME_V20_winter_final", "Winter's Gate", "Tonight the weak gods die 🐺 Epic Power Metal",
  "Blood on the snow, a vow beneath the frozen sky — and the hunt that never ends.",
  "Who are the 'weak gods' in your life?", "#powermetal #epicmetal #vikingmetal"),
 ("WME_V21_stars_chorus", "When the Stars remember US", "If I never come home… 🌌 Symphonic Metal Ballad",
  "A letter in a soldier's coat, a promise under a violet sky: love will be the final signal.",
  "Who would you come home for?", "#symphonicmetal #metalballad #femalevocals"),
 ("WME_V22_blood_chorus", "Blood for the Red Angel", "Only rage remains 🩸 Groove Thrash Metal",
  "Once a son with a warrior's soul. Now a storm no chain can hold.",
  "Can rage ever be a gift — or is it always a curse?", "#thrashmetal #groovemetal #metal"),
 ("WME_V23_blood_final", "Blood for the Red Angel", "When the last bell tolls 🔔 Thrash Metal",
  "Every prayer becomes a scream. When the final bell is tolling, only rage remains.",
  "What would you fight for when hope is gone?", "#thrashmetal #heavymetal #metal"),
 ("WME_V24_children_chorus", "Children of the Void", "They eat the stars 🌑 Cosmic Thrash Metal",
  "A hunger with no face, no hatred, no pride — world after world goes silent.",
  "What's scarier: an enemy that hates you or one that doesn't care?", "#thrashmetal #cosmichorror #metal"),
 ("WME_V25_children_bridge", "Children of the Void", "If they are hunger, we are flame 🔥 Thrash Metal",
  "If they are legion, we are name. If they are night without a face — we are the wrath of the human race.",
  "Flame or name — which line hits harder?", "#thrashmetal #epicmetal #metal"),
 ("WME_V26_machine_chorus", "Machine God Rising", "Flesh is weak. Steel is truth. ⚙️ Industrial Metal",
  "Binary hymns in a cathedral of chrome — the ancient machine is awake.",
  "Would you trade your flesh for iron?", "#industrialmetal #powermetal #metal"),
 ("WME_V27_machine_final", "Machine God Rising", "Iron keeps the sacred trust 🔩 Industrial Power Metal",
  "Flesh will fail and bone will rust. The forge still sings.",
  "Is a soul still a soul inside a machine?", "#industrialmetal #epicmetal #metal"),
 ("WME_V28_green_chorus", "Green Tide Rising", "Laughing as they kill 🪓 Groove Thrash Metal",
  "Scrap-built thunder, rust and fire — there is no wall against the tide.",
  "Would you rather face the tide or ride with it?", "#groovemetal #thrashmetal #metal"),
 ("WME_V29_green_final", "Green Tide Rising", "When the galaxy wants silence… 📢 Thrash Metal",
  "They bring the noise, the fire and the end of everything.",
  "Louder, faster or harder — what do you pick?", "#thrashmetal #groovemetal #metal"),
 ("WME_V30_stars_final", "When the Stars remember US", "Keep one candle in the dark 🕯️ Symphonic Metal",
  "If I return with a broken heart, I will love you even more.",
  "Who keeps a candle in the dark for you?", "#symphonicmetal #metalballad #femalevocals"),
]

ORDER = ["V01", "V18", "V07", "V15", "V09", "V04", "V12", "V22", "V02", "V24", "V21", "V17", "V26", "V08", "V20",
         "V28", "V11", "V06", "V14", "V23", "V16", "V25", "V10", "V05", "V27", "V19", "V03", "V29", "V30", "V13"]
SLOTS = ["12:00", "16:00", "19:00"]


def main():
    by = {s[0].split("_")[1]: s for s in S}
    rows = []
    d0 = date(2026, 11, 23)
    for n, key in enumerate(ORDER):
        sid, track, title, story, q, tags = by[key]
        url = f"https://youtu.be/{FULL[track]}"
        hs = " ".join(dict.fromkeys((tags + " #metal #shorts").split()))  # без повторов хэштегов
        desc = f"{story}\n\nFull song: {url}\n{STREAM}\n{SLOGAN}\n\n{DISC}\n\n{hs}"
        day = d0 + timedelta(days=n // 3)
        rows.append({"id": sid, "file": sid + ".mp4", "track": track, "full_video": FULL[track], "title": title,
                     "description": desc, "pinned_comment": q, "tags": TAGS_BASE,
                     "date": day.isoformat(), "time_msk": SLOTS[n % 3],
                     "playlist": "", "made_for_kids": False, "ai_altered": True})
    json.dump(rows, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = ["---", "name: Shorts v2 WME — метаданные и график",
          "description: 30 Shorts World Metal Empire (шаблон v2) — заголовки, описания, закрепы и расписание 3 в день с 23.11.2026",
          "type: project", "---", "", "# Shorts v2 World Metal Empire — метаданные и график", "",
          "Файлы: `Канал1_World_Metal_Empire\\Shorts_v2\\<id>.mp4`. Машинная версия — `shorts_v2_meta.json` рядом.",
          "В Studio у каждого: Not made for kids · Altered/synthetic content = Yes · Related video = полный трек · "
          "в альбомный плейлист НЕ добавлять (сломает ручной порядок треков; решение 22.11) · Schedule на указанное время (МСК). "
          "Закреп-комментарий — после выхода ролика.", "", "**Статус файлов (22.11.2026, 13:15 МСК): все 30 роликов окончательны и проверены — можно загружать все, включая V04–V06, V09–V14, V21–V30.**", "",
          "Теги (одни на все): " + ", ".join(TAGS_BASE), "",
          "| # | Дата | МСК | Файл | Заголовок | Полный трек | Закреп |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        md.append(f"| {i} | {r['date'][8:]}.{r['date'][5:7]} | {r['time_msk']} | {r['id']} | {r['title']} | "
                  f"{r['full_video']} | {r['pinned_comment']} |")
    md += ["", "## Шаблон описания", "", "```", rows[0]["description"], "```", ""]
    open(sys.argv[1], "w", encoding="utf-8").write("\n".join(md))
    print("ok", len(rows))


if __name__ == "__main__":
    main()
