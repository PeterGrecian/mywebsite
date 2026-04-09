"""Gotterdammerung on the Go page."""

def render_gotg_page(*, theme_css_js):
    """Render Götterdämmerung on the Go — scene-by-scene listening guide with liner notes."""
    scenes = [
        {
            'num': 1, 'title': 'The Norns', 'act': 'Prologue',
            'tracks': '1–4', 'duration': '19:19',
            'location': "Brünnhilde's rock, night",
            'characters': 'Three Norns (Daughters of Erda)',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/b/b2/Siegfried_and_the_Twilight_of_the_Gods_p_104.jpg',
            'img_credit': 'Arthur Rackham, 1911',
            'synopsis': 'Three fate-weaving Norns recount the history of gods and the Ring while passing a golden rope between them. The First Norn recalls Wotan breaking a branch from the World Ash Tree to make his spear of law. The Second tells how Siegfried shattered that spear. The Third sees Valhalla surrounded by piled wood, awaiting fire. The rope tangles, the weaving grows desperate — and the rope <strong>breaks</strong>. Fate itself has ended. In terror, they vanish to their mother Erda. Dawn breaks.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260317_180040500.jpg',
            'atmos_alt': 'London skyline at dusk — twilight of the gods',
            'atmos_credit': 'Peter Grecian',
            'performers': '<img class="perf-photo" src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/Birgitta_Svend%C3%A9n_2013.jpg/150px-Birgitta_Svend%C3%A9n_2013.jpg" alt="Birgitta Svendén"><strong>Birgitta Svenden</strong> (First Norn) — Swedish mezzo, Bayreuth regular 1983-99, later General Manager of the Royal Swedish Opera. <strong>Linda Finnie</strong> (Second Norn / also Waltraute in Scene 5) — Scottish contralto, one of the recording\'s standout voices. <strong>Uta Priew</strong> (Third Norn) — German mezzo, long collaboration with director Harry Kupfer who staged this production.',
            'context': 'Wagner wrote this scene <em>last</em> (1874), even though it comes first — a Greek-chorus prologue framing the human drama within cosmic twilight. The three women deliberately echo Shakespeare\'s Weird Sisters in <em>Macbeth</em>, but with a crucial difference: Shakespeare\'s witches tempt the hero toward doom through ambiguous prophecy; Wagner\'s Norns are helpless witnesses whose power breaks, making way for genuine human choice.',
            'quote': '<em>"Es riss! Es riss!"</em> — It broke! It broke!',
            'musical': 'Low strings create primordial darkness. Chromatic harmonies dissolve as the Norns weave faster. Listen for fragmenting Valhalla and World Ash motifs colliding as order breaks down. Three female voices pass phrases like the rope — overlapping entries, shared melodic material, increasing agitation.',
            'tip': 'Focus on atmosphere and the rope breaking (Track 4, final minutes). The rope breaking is the opera\'s thesis statement: determinism has ended, human choice becomes possible.',
            'playlist': 'PLeMsytZrLIuY-6MBFLlOFGhKEm-Ft6pvF',
        },
        {
            'num': 2, 'title': 'Farewell & Rhine Journey', 'act': 'Prologue',
            'tracks': '5–10', 'duration': '21:14',
            'location': "Brünnhilde's rock, then the Rhine",
            'characters': 'Brünnhilde, Siegfried',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/9/9b/Ring52.jpg',
            'img_credit': 'Arthur Rackham, 1911',
            'synopsis': 'Dawn breaks. Siegfried and Brünnhilde emerge from their night together for an ecstatic farewell. She urges him to new deeds; he gives her the Ring as a love-token. She gives him her horse Grane and her wisdom. He rejects wisdom: <em>"my own valor is enough"</em> — this is his tragic flaw, not arrogance but innocence. They part in joy. Neither suspects what\'s coming. The orchestral Rhine Journey (Track 10) depicts Siegfried\'s descent from the mythic heights into the corrupt world below.',
            'performers': '<strong>Anne Evans</strong> (Brünnhilde) — British soprano, DBE, combined vocal power with profound dramatic intelligence. Bayreuth 1989-92. Her Immolation Scene (Scene 12) is the recording\'s crown. <strong>Siegfried Jerusalem</strong> (Siegfried) — German Heldentenor, originally a bassoonist. One of the last great heroic tenors who combined Wagnerian power with lyrical beauty.',
            'context': 'This is the last time Brünnhilde and Siegfried are happy and together. Everything that follows is betrayal, confusion, and catastrophe. Siegfried giving the Ring seems loving, but it removes the curse-bearer from the hero who might break it and places it within the Gibichungs\' reach.',
            'quote': '<em>"Zu neuen Taten, teurer Helde"</em> — To new deeds, dear hero',
            'musical': 'Track 10 (Siegfried\'s Rhine Journey) is one of Wagner\'s greatest orchestral passages — a tone poem shifting from heroic C-major horn calls through nature motifs to darker harmonies. It works as a standalone concert piece. The transition from bright major to ominous minor mirrors the journey from myth to modernity.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260317_134623360.jpg',
            'atmos_alt': 'London panorama through office window — the journey begins',
            'atmos_credit': 'Peter Grecian',
            'tip': 'This is the last moment of happiness. Follow the horn calls in Track 10 as they darken — Siegfried approaches the Gibichung hall and his doom.',
            'playlist': 'PLeMsytZrLIubnRWkKqmcWRJsm6cgMj-su',
        },
        {
            'num': 3, 'title': "Hagen's Plot", 'act': 'Act 1',
            'tracks': '11–20', 'duration': '32:42',
            'location': 'Gibichung Hall by the Rhine',
            'characters': 'Hagen, Gunther, Gutrune, Siegfried',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/e/e7/Siegfried_and_the_Twilight_of_the_Gods_p_120.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Siegfried hands the drinking-horn back to Gutrune',
            'synopsis': 'The scene shifts from mythic heights to mundane ambition. Hagen manipulates his half-siblings: Gunther (weak king wanting reputation) needs a wife, Gutrune needs a husband. His solution: a potion to make Siegfried forget Brünnhilde, marry Gutrune, then use the Tarnhelm to fetch Brünnhilde for Gunther. Siegfried arrives, drinks the welcome cup — memory erased. He instantly forgets his love and becomes infatuated with Gutrune. They swear blood-brotherhood (<em>Blutbruderschaft</em>) and depart to abduct Brünnhilde. Wagner\'s irony: the Ring\'s freest hero, reduced to puppet through chemistry.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260109_101519827.jpg',
            'atmos_alt': 'Guildhall — a medieval great hall in the City',
            'atmos_credit': 'Peter Grecian',
            'performers': '<img class="perf-photo" src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/Eva-Maria_Bundschuh_1987.jpg/150px-Eva-Maria_Bundschuh_1987.jpg" alt="Eva-Maria Bundschuh, 1987"><strong>Philip Kang</strong> (Hagen) — Korean-German bass, the <em>first Asian singer to perform major Wagnerian roles at Bayreuth</em> (1988-92). His Hagen embodied pure malevolence with unsettling stillness. <strong>Bodo Brinkmann</strong> (Gunther) — German baritone, portrayed Gunther as nobility without strength. <strong>Eva-Maria Bundschuh</strong> (Gutrune, pictured 1987) — German soprano, innocence destroyed by proximity to power.',
            'context': 'The Gibichungs represent modernity\'s mediocrity — bureaucrats and social climbers inheriting a heroic age they can\'t comprehend. They use technology (potion, Tarnhelm) rather than authentic strength. Wagner saw them as the German bourgeoisie after 1848. Siegfried isn\'t cursed or fated — he\'s <em>drugged</em>. This makes the tragedy more disturbing than divine manipulation.',
            'quote': '<em>"Willkommen, Gast, in Gibichs Haus!"</em> — Welcome, guest, to Gibich\'s house!',
            'musical': 'Listen for the orchestral transformation at Track 17: Siegfried toasts "Brünnhilde!" — drinks — the love theme inverts into hollow emptiness — a new false-love theme for Gutrune emerges. Psychological destruction through leitmotif manipulation.',
            'tip': 'The potion scene (Track 17) is devastating. The blood oath (Track 19) is a dark parody of heroic music — solemn ritual for a manipulated alliance.',
            'playlist': 'PLeMsytZrLIubQfPCF2hUF3BrGxw4gCnlZ',
        },
        {
            'num': 4, 'title': "Hagen's Watch", 'act': 'Act 1',
            'tracks': '21', 'duration': '11:08',
            'location': 'Gibichung Hall, night',
            'characters': 'Hagen (alone)',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/d/d4/Siegfried_and_the_Twilight_of_the_Gods_p_128.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; The ravens of Wotan',
            'synopsis': 'Everyone has departed. Hagen sits alone in darkness — 11 minutes of pure malevolence. He reveals his true thoughts: he manipulates Gunther and Gutrune like puppets; he\'ll get the Ring for his father Alberich; once he has it, the Nibelungs will rule the world. He never sleeps. The scene ends with him motionless, watching.',
            'performers': '<strong>Philip Kang</strong> — His Watch scene remains one of the most chilling performances of Wagner\'s patient villain. Lean, focused, modern psychology rather than cartoonish evil.',
            'context': 'Like Iago in <em>Othello</em> or Richard III, Hagen reveals himself to the audience alone. But Iago improvises brilliantly; Hagen plans methodically. Iago is Renaissance villainy (wit, improvisation). Hagen is industrial-era villainy (system, patience, instrumentalism). Wagner, influenced by Schopenhauer, saw Hagen as pure will-to-power without being — all striving, no rest. He never sleeps: the nightmare of modernity, perpetual vigilance.',
            'quote': '<em>"Hier sitz\' ich zur Wacht, wahre den Hof"</em> — Here I sit on watch, guard the court<br><small>(Irony: the real threat comes from inside — from Hagen himself.)</small>',
            'musical': 'Built over an obsessive ground bass — repeating, immobile, representing Hagen\'s fixed will and the curse\'s inexorable working. Dark low brass, no upper-register warmth. Wagner wrote this for a true <em>basso profondo</em>, rare even in his time.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260206_133202622.MP.jpg',
            'atmos_alt': 'City in rain — watching over London',
            'atmos_credit': 'Peter Grecian',
            'tip': 'True power doesn\'t need to move. It waits. The stillness is the menace. Compare with Wotan\'s monologues — where Wotan despairs, Hagen calculates.',
            'playlist': 'PLeMsytZrLIuYrGX5nB_kYbjJjYnjM1LKn',
        },
        {
            'num': 5, 'title': "Waltraute's Plea", 'act': 'Act 1',
            'tracks': '22–24', 'duration': '26:36',
            'location': "Brünnhilde's rock",
            'characters': 'Brünnhilde, Waltraute',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/0/08/Siegfried_and_the_Twilight_of_the_Gods_p_130.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; The Ring upon thy hand',
            'synopsis': 'Brünnhilde hears approaching sounds — Siegfried returning? No: her Valkyrie sister Waltraute, with devastating news. In the opera\'s most important narrative passage (Track 23, 12 minutes), Waltraute describes Wotan\'s current state: broken, silent, sitting in Valhalla holding pieces of his shattered spear, dead World Ash wood piled around the hall awaiting fire. Once, Wotan muttered: <em>"If Brünnhilde returned the Ring to the Rhine, gods and world would be redeemed."</em> Waltraute begs. Brünnhilde refuses — the Ring is Siegfried\'s love-token, more precious than Valhalla, more precious than the gods.',
            'performers': '<strong>Linda Finnie</strong> (Waltraute / also Second Norn) — Her Waltraute scene is one of the recording\'s most powerful moments, sustaining both narrative power and emotional depth across nearly half an hour of continuous performance.',
            'context': 'Wotan doesn\'t appear in Gotterdammerung (he dominated the previous operas). His absence is the point — he\'s given up. Cosmic depression: the god of will has lost his will. Brünnhilde must choose: save the gods (return the Ring, obey Wotan\'s indirect command) or keep Siegfried\'s love. She chooses love — humanity over divinity. The dramatic irony is crushing: the Ring she defends as symbol of his love... Siegfried doesn\'t even remember her.',
            'quote': '<em>"Den Ring geb\' ich nicht — eher vergeh\' die Welt!"</em> — I\'ll not give up the Ring — let the world perish first!',
            'musical': 'Waltraute\'s 12-minute narrative uses recitative-like flexibility with orchestral leitmotif commentary — Valhalla majestic but now tragic, the World Ash dying, Wotan\'s spear shattered. Words tell story; orchestra tells meaning.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260220_165308688.jpg',
            'atmos_alt': 'St Paul\'s under grey skies — the gods\' broken world',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Track 23 is a mini-opera within the opera. This is Wagner\'s most powerful messenger scene — 26 minutes of continuous dramatic narrative.',
            'playlist': 'PLeMsytZrLIuYPuDwIpTVy4cKDNL-iKKB4',
        },
        {
            'num': 6, 'title': 'The Abduction', 'act': 'Act 1',
            'tracks': '25–26', 'duration': '12:51',
            'location': "Brünnhilde's rock",
            'characters': 'Brünnhilde, Siegfried (disguised as Gunther)',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/5/52/Siegfried_and_the_Twilight_of_the_Gods_p_124.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Brünnhilde kisses the Ring',
            'synopsis': 'Storm clouds. Lightning. A figure approaches through the fire — Brünnhilde joyfully assumes Siegfried returns. But the figure emerges as a stranger claiming to be Gunther. (Actually: Siegfried wearing the Tarnhelm.) She holds up the Ring — its magic should protect her. It doesn\'t. He overpowers her, rips the Ring from her finger, drags her into the cave. He places his sword Nothung between them — technically keeping faith with Gunther, but Brünnhilde won\'t know this. She is broken.',
            'performers': '',
            'context': 'From Brünnhilde\'s perspective: a stranger has violated her sanctuary, stolen Siegfried\'s Ring, overpowered her by force. From Siegfried\'s: he\'s helping his blood-brother, keeping his oath, even preserving "honour" with the sword. The potion has made him amnesiac, not evil. But the effect is evil regardless. The man she loves is the man who betrays her — and neither knows they\'re the same person.',
            'quote': '<em>"Brünnhild\'! Ein Freier kam"</em> — Brünnhilde! A suitor came',
            'musical': 'Storm music in Track 25: lightning (brass stabs), thunder (timpani rolls), wind (swirling strings). In Track 26, listen for Siegfried\'s hero motifs underneath "Gunther\'s" voice — the orchestra tells us who he really is, even as she can\'t recognise him.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260106_120336771.jpg',
            'atmos_alt': 'Barbican in snow — storm and violation',
            'atmos_credit': 'Peter Grecian',
            'tip': 'The dramatic irony is devastating. The sword between them echoes the Volsung saga. Act 1 curtain falls on her devastation.',
            'playlist': 'PLeMsytZrLIuZFMCKLSvNuzF7kzPedqdyk',
        },
        {
            'num': 7, 'title': 'Night Conspiracy', 'act': 'Act 2',
            'tracks': '27–29', 'duration': '12:42',
            'location': 'Gibichung hall, night',
            'characters': 'Hagen, Alberich',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/a/a5/Alberich_hagen.jpg',
            'img_credit': 'Arthur Rackham, 1912 &mdash; Swear to me, Hagen, my son!',
            'synopsis': 'Darkness. Hagen sits motionless (does he ever sleep?). His father Alberich — the Nibelung dwarf who forged the Ring and cursed it — appears in a nightmare-vision. Wagner leaves it ambiguous: dream or reality? Father and son share their hatred of the gods. Alberich\'s urgency: Wotan is broken, but Siegfried has the Ring and is dangerously fearless. <em>"Swear it!"</em> Hagen swears to get the Ring. Alberich vanishes. Dawn approaches.',
            'performers': '<strong>Gunter von Kannen</strong> (Alberich) — German bass-baritone (1940-2016). Received his breakthrough from Barenboim in the 1982 Harry Kupfer Ring and continued to portray the cycle\'s original villain throughout his career.',
            'context': 'Two generations of Ring-curse: Alberich renounced love for power and forged the Ring; Hagen inherits lovelessness and pursues it for father. Neither chose this path — they were shaped by the curse itself. Wagner\'s question: can you be responsible for evil you inherited? Hagen\'s tragedy (if he has one): he never had a chance.',
            'quote': '<em>"Schlafst du, Hagen, mein Sohn?"</em> — Are you sleeping, Hagen, my son?',
            'musical': 'Oppressive orchestral darkness. Alberich\'s motifs from Das Rheingold return — the curse made flesh, passed from father to son. The Ring curse dominates the scene.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260310_162109975.MP.jpg',
            'atmos_alt': 'Dramatic clouds over London — darkness gathering',
            'atmos_credit': 'Peter Grecian',
            'tip': 'This brief scene connects Gotterdammerung back to Das Rheingold where it all began. Listen for the Rheingold harmonies.',
            'playlist': 'PLeMsytZrLIubn_iS0OkdhLllw8JsFusao',
        },
        {
            'num': 8, 'title': 'Vassals & Confrontation', 'act': 'Act 2',
            'tracks': '30–40', 'duration': '44:17',
            'location': 'Gibichung hall, public gathering',
            'characters': 'Siegfried, Hagen, Gutrune, Gunther, Brünnhilde, Vassals',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/c/cc/Wagner_-_G%C3%B6tterd%C3%A4mmerung_-_Setting_of_act_II_at_Bayreuth_-_The_Victrola_book_of_the_opera.jpg',
            'img_credit': 'Act II at Bayreuth, from The Victrola Book of the Opera',
            'synopsis': 'Siegfried returns triumphant. Hagen summons vassals with his war horn. When Gunther arrives with veiled, broken Brünnhilde, she sees the Ring on Siegfried\'s finger — the one torn from her last night. Her head snaps up: <em>"Siegfried?! Here?!"</em> She nearly faints. Public accusation erupts. Both swear oaths on Hagen\'s spear: he swears he never wronged her (the potion erased his memory — technically true), she swears he\'s lying (she experienced the abduction — also technically true). Both pour everything into contradictory truths. The contradiction destroys Brünnhilde. Siegfried dismisses her — <em>"her grief disturbs her mind"</em> — and leads Gutrune away to celebrate, cheerful and oblivious.',
            'performers': '',
            'context': 'Hagen\'s perfect crime: he never lies or even speaks much. He gave Siegfried the potion (chemical truth-alteration), suggested the abduction (exploiting amnesia), offered his spear for the oath (neutral arbiter), and watches the truth destroy them (passive observation). The crime is structural — he arranged conditions where truth conflicts with truth. Hagen\'s spear echoes Wotan\'s (divine law), but inverted: justice without mercy, pure retribution. This spear will kill Siegfried in Act 3.',
            'quote': '<em>"Helle Wehr! Heilige Waffe! Hilf meinem ewigen Eide!"</em> — Shining weapon! Holy steel! Witness my eternal oath!',
            'musical': 'The vassals\' chorus is Wagner\'s biggest choral writing in the Ring. The oath-swearing is electrifying — Siegfried\'s confident heroic brass against Brünnhilde\'s jagged desperate leaps, the orchestra undermining both with Ring and Curse motifs. She calls on the gods for witness — they are silent.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260113_100124014.jpg',
            'atmos_alt': 'Waterloo station — the crowd gathers',
            'atmos_credit': 'Peter Grecian',
            'tip': 'The oath duel (Tracks 38-40) is the opera\'s dramatic peak before the murder. Notice what Siegfried <em>doesn\'t hear</em>: the orchestra plays Brünnhilde\'s love theme when she speaks, but he remains unmoved.',
            'playlist': 'PLeMsytZrLIubLA1zF0CDOvFQDzfgfjCsR',
        },
        {
            'num': 9, 'title': 'The Murder Plot', 'act': 'Act 2',
            'tracks': '41–45', 'duration': '17:40',
            'location': 'Gibichung hall',
            'characters': 'Brünnhilde, Hagen, Gunther',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/e/ed/Siegfried_and_the_Twilight_of_the_Gods_p_154.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; O wife betrayed, I will avenge thy trust deceived',
            'synopsis': 'Three conspirators remain, each with different reasons. Brünnhilde, destroyed by betrayal, reveals Siegfried\'s one vulnerability: his back — she never shielded it with magic, assuming he\'d never retreat. <em>"And my spear shall find that spot,"</em> says Hagen coldly. Gunther wavers — <em>"He\'s my blood-brother"</em> — but his honour is already shattered. Hagen barely needs to manipulate: he asks questions, states facts, offers solutions. The murder will be disguised as a hunting accident. Act 2 ends in conspiracy — three figures backlit, the Ring curse grinding in the orchestra.',
            'performers': '',
            'context': 'Brünnhilde betrays Siegfried exactly as she believes he betrayed her. She gave him invincibility out of love; she now tells his enemies how to kill him out of rage. Wagner shows that rage is love inverted — same intensity, opposite direction. She doesn\'t realise she\'s serving Hagen\'s deeper plan. Gunther is pitiable, not villainous — a weak man dragged into murder, whose every line shows hesitation.',
            'quote': '<em>"Seinen Rucken doch traf ihn kein Feind — er bot keinem je ihn dar"</em> — His back no enemy ever struck — he never turned it to a foe',
            'musical': 'Brünnhilde\'s music twists from love themes into vengeance. A new revenge motif emerges — aggressive, march-like. Hagen\'s Watch theme stays underneath, guiding without dominating. Notice how Gunther\'s vocal line keeps reaching up (hoping for a way out) while Hagen\'s stays low and level (inexorable).',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260128_163302319.MP.jpg',
            'atmos_alt': 'Industrial ceiling — cold machinery of conspiracy',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Three motivations, one murder: Brünnhilde wants emotional vengeance, Gunther wants social restoration, Hagen wants the Ring. Only Hagen will achieve his goal.',
            'playlist': 'PLeMsytZrLIuawa4erw8Uz4XAeln97N1Oz',
        },
        {
            'num': 10, 'title': "Rhine Maidens' Warning", 'act': 'Act 3',
            'tracks': '46–52', 'duration': '20:01',
            'location': 'The Rhine, forest',
            'characters': 'Woglinde, Wellgunde, Flosshilde, Siegfried',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/4/46/Siegfried_rhinemaidens.jpg',
            'img_credit': 'Arthur Rackham, 1912 &mdash; Rhine Maidens warn Siegfried',
            'synopsis': 'Dawn on the Rhine. The three Rhine Maidens swim and sing, mourning their lost gold. Siegfried, separated from the hunting party, stumbles upon them. They flirt playfully, asking for the Ring. He almost gives it for fun — then pauses. They turn serious: <em>"Keep it, hero — if you only knew what curse it holds. Give it back to us — we alone can free it."</em> He laughs and refuses. They swim away prophesying his death: <em>"By evening, a woman will inherit the Ring — she\'ll listen to us better."</em> He blows his horn and rejoins the hunt.',
            'performers': '<strong>Hilde Leidland</strong> (Woglinde) — Norwegian soprano (1958-2007). <strong>Annette Kuttenbaum</strong> (Wellgunde) — German mezzo. <strong>Jane Turner</strong> (Flosshilde) — British contralto.',
            'context': 'This scene mirrors Das Rheingold Scene 1 — the cycle\'s opening: same gold, same maidens, same request. But now corrupted. Siegfried\'s refusal makes perfect sense: he\'s never known fear, never experienced loss, never needed consequences. His absolute fearlessness is beautiful but fatal. Wisdom requires acknowledging forces greater than oneself. This is his last chance to escape the curse.',
            'quote': '<em>"Kommt, Schwestern! Schwindet dem Toren!"</em> — Come, sisters! Away from the fool!',
            'musical': 'The Rhine motif returns in its original, uncorrupted form — first heard in Das Rheingold, fragmented throughout the cycle, here briefly restored. Playful water music in thirds darkens into prophecy. Siegfried\'s horn call remains bright and defiant.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260225_102739209.jpg',
            'atmos_alt': 'Tate Modern and the south bank in haze — the river',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Track 47 (the Maidens\' opening song) is one of Wagner\'s most beautiful lyric passages. Savour the pure Rhine music before human drama returns.',
            'playlist': 'PLeMsytZrLIuaVkM4mbNv8MtSq0wFWhfNS',
        },
        {
            'num': 11, 'title': 'Hunt, Narration & Murder', 'act': 'Act 3',
            'tracks': '53–58', 'duration': '19:12',
            'location': 'Forest clearing',
            'characters': 'Siegfried, Hagen, Gunther, Vassals',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/a/aa/Siegfried_and_the_Twilight_of_the_Gods_p_172.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Siegfried\'s death',
            'synopsis': 'Midday rest during the hunt. Hagen suggests Siegfried tell his life story. He narrates his youth — Mime, reforging Nothung, killing Fafner, understanding birdsong. The orchestra replays the entire Siegfried opera in miniature. Then he stops: memory ends where the potion took hold. Hagen hands him a drink — <em>"this will refresh your memory."</em> Siegfried\'s face changes. Memory floods back: <em>"Brünnhilde! I remember! She woke, and we —"</em> Two ravens fly up. Hagen: <em>"Do you understand those ravens\' cries? They tell me: Revenge!"</em> He drives the spear into Siegfried\'s back. Siegfried\'s dying vision is of Brünnhilde: <em>"Holy bride! Awake! Open your eyes!"</em> He dies calling her name.',
            'performers': '',
            'context': 'Hagen\'s final sadism: restoring Siegfried\'s memory before killing him. He wants Siegfried to die knowing he betrayed Brünnhilde — even though the betrayal was involuntary. The murder would work without restored memory; Hagen adds it for personal satisfaction. This is the mark of Alberich\'s son: unnecessary malice. Yet Wagner grants mercy — Siegfried escapes the Gibichung world (lies, manipulation, politics) and returns in death to the mountain, the fire, the awakening.',
            'quote': '<em>"Brünnhilde! Heilige Braut! Wach auf! Offne dein Auge!"</em> — Brünnhilde! Holy bride! Awake! Open your eyes!',
            'musical': 'Siegfried\'s narration replays leitmotifs from the entire cycle — his life in music. The memory-restoring drink inverts the potion motif. Then the murder: a shocking orchestral blow. His 5-minute death scene builds from weakness to one transcendent burst of full-strength tenor, then fades. Listen for the orchestral silence — two full beats of nothing — before the Funeral March begins.',
            'atmos_img': 'https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/PXL_20260305_153732877.MP.jpg',
            'atmos_alt': 'South London sprawl — the hunting ground',
            'atmos_credit': 'Peter Grecian',
            'tip': 'Track 57 contains memory restoration, ravens, and murder — all in 2:15. One of opera\'s most efficient catastrophes. Track 58 (the death) — Siegfried dies remembering love, not heroism. The orchestra weeps.',
            'playlist': 'PLeMsytZrLIubt28DLEYg3_7NmUWR1GSRL',
        },
        {
            'num': 12, 'title': "Funeral March, Immolation & End", 'act': 'Act 3',
            'tracks': '59–69', 'duration': '41:10',
            'location': 'Forest, Gibichung hall, and beyond',
            'characters': 'Orchestra, Gutrune, Hagen, Gunther, Brünnhilde',
            'img': 'https://upload.wikimedia.org/wikipedia/commons/7/7f/Ring63.jpg',
            'img_credit': 'Arthur Rackham, 1911 &mdash; Brünnhilde leaps onto the funeral pyre',
            'synopsis': '<strong>Funeral March</strong> (Track 59, 6:14): The orchestra alone eulogises Siegfried — five phases recounting his youth, heroism, love, and loss. No words needed; the music <em>is</em> the biography. <strong>Aftermath</strong> (Tracks 60-63): Back at the hall, Hagen lies about a boar. Gunther reveals the truth. They fight over the Ring. Hagen kills Gunther. When Hagen reaches for the Ring, <strong>the corpse\'s hand rises</strong> — Hagen recoils in terror. The curse protects itself. <strong>Immolation</strong> (Tracks 64-69): Brünnhilde enters, silences everyone, and speaks with recovered divine authority. She orders the pyre, takes the Ring, understands Wotan\'s design at last: <em>"The world built on power and law is broken. Love alone redeems, but love requires sacrifice."</em> She returns the Ring to the Rhine, commands Loge to burn Valhalla, and rides Grane into the flames. The Rhine floods. The Rhine Maidens reclaim the gold. Hagen drowns reaching for it. Valhalla burns. The Redemption through Love motif rises — ascending, radiant. The orchestra holds the final chord. Curtain.',
            'performers': '<strong>Anne Evans</strong> — Her Immolation is intelligently paced, emphasising text clarity. Her final <em>"Siegfried!"</em> has genuine joy — not despair.',
            'context': 'Brünnhilde\'s final understanding: Wotan needed a free hero (Siegfried) and a free woman (herself) to make the choice he could not command. Only free will — unconstrained by divine law — can truly redeem. The Ring cycle ends where it began: at the Rhine. The gold is returned, the curse lifted, the gods gone. Whether this is tragedy or hope — whether the cycle repeats or humanity learns — Wagner leaves unanswered. <em>The music resolves. The story does not.</em>',
            'quote': '<em>"Ruhe, ruhe, du Gott!"</em> — Rest, rest, you god!',
            'musical': 'Every major leitmotif from all four Ring operas returns: Rhine, Valhalla, Ring curse, Alberich\'s renunciation, Brünnhilde\'s love, Siegfried\'s horn, forest murmurs, Norns, immolation, and finally Redemption through Love — ascending D-flat major, strings shimmering. Musical architecture on an unprecedented scale.',
            'tip': 'Track 59 (Funeral March) is arguably Wagner\'s single greatest orchestral passage — listen with no distractions. The final 90 seconds of Track 69: the Redemption through Love motif was hinted at throughout 15+ hours of music; here it finally, fully, resolves.',
            'playlist': 'PLeMsytZrLIuYZv3LbHwFiEoBxfsxXN2QH',
        },
    ]

    # Group by act
    acts = {}
    for s in scenes:
        acts.setdefault(s['act'], []).append(s)

    # Build table of contents
    toc_html = '<nav class="toc"><div class="toc-title">Contents</div>\n'
    for act_name in ['Prologue', 'Act 1', 'Act 2', 'Act 3']:
        act_id = act_name.lower().replace(' ', '')
        toc_html += f'<div class="toc-act">{act_name}</div>\n'
        for s in acts.get(act_name, []):
            toc_html += f'<a class="toc-scene" href="#scene-{s["num"]}">{s["num"]}. {s["title"]}</a>\n'
    toc_html += '</nav>\n'

    cards_html = ''
    for act_name in ['Prologue', 'Act 1', 'Act 2', 'Act 3']:
        act_id = act_name.lower().replace(' ', '')
        # Inline mini-TOC before Act 2 and Act 3
        if act_name in ('Act 2', 'Act 3'):
            mini = '<nav class="toc mini-toc">\n'
            for a in ['Prologue', 'Act 1', 'Act 2', 'Act 3']:
                current = ' style="color:var(--text);font-weight:600"' if a == act_name else ''
                mini += f'<span class="toc-act">{a}</span>\n'
                for sc in acts.get(a, []):
                    mini += f'<a class="toc-scene"{current if a == act_name else ""} href="#scene-{sc["num"]}">{sc["num"]}. {sc["title"]}</a>\n'
            mini += '</nav>\n'
            cards_html += mini
        cards_html += f'<h2 class="act-heading" id="{act_id}">{act_name}</h2>\n'
        for s in acts.get(act_name, []):
            ytm_url = f"https://music.youtube.com/playlist?list={s['playlist']}"
            performers_html = f'<details class="scene-details"><summary>The performers</summary><div class="performers-content">{s["performers"]}</div></details>' if s.get('performers') else ''
            atmos_html = f'<div class="scene-img atmos"><img src="{s["atmos_img"]}" alt="{s["atmos_alt"]}" loading="lazy"><span class="img-credit">{s["atmos_credit"]}</span></div>' if s.get('atmos_img') else ''
            cards_html += f'''<div class="scene-card" id="scene-{s['num']}">
  <div class="scene-header">
    <div class="scene-num">{s['num']}</div>
    <div class="scene-info">
      <div class="scene-title">{s['title']}</div>
      <div class="scene-meta">Tracks {s['tracks']} &middot; {s['duration']} &middot; {s['location']}</div>
      <div class="scene-chars">{s['characters']}</div>
    </div>
    <a href="{ytm_url}" target="_blank" class="ytm-btn" title="Play on YouTube Music">&#9654;</a>
  </div>
  <div class="scene-img"><img src="{s['img']}" alt="{s['title']}" loading="lazy"><span class="img-credit">{s['img_credit']}</span></div>
  {atmos_html}
  <p class="scene-synopsis">{s['synopsis']}</p>
  <blockquote class="scene-quote">{s['quote']}</blockquote>
  {performers_html}
  <details class="scene-details"><summary>Dramatic context</summary><p>{s['context']}</p></details>
  <details class="scene-details"><summary>Musical features</summary><p>{s['musical']}</p></details>
  <details class="scene-details"><summary>Listening tip</summary><p>{s['tip']}</p></details>
</div>
'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gotterdammerung on the Go</title>
  <link rel="icon" type="image/png" sizes="192x192" href="https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-192.png">
  <link rel="manifest" href="/gotg/manifest.json">
  <meta name="theme-color" content="#000000">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
  <link rel="apple-touch-icon" href="https://s3-eu-west-1.amazonaws.com/www.petergrecian.co.uk/assets/gotg/icon-192.png">
  {theme_css_js}
  <style>
    body {{ font-family: var(--font); background: var(--bg); color: var(--text); margin: 0; padding: 1rem; }}
    .container {{ max-width: 700px; margin: 0 auto; }}
    h1 {{ text-align: center; font-size: 1.6rem; margin: 1.5rem 0 0.3rem; }}
    .subtitle {{ text-align: center; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.3rem; }}
    .recording-info {{ background: var(--card-bg); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.6; }}
    .recording-info a {{ color: var(--accent); text-decoration: none; }}
    .recording-info strong {{ color: var(--text); }}
    .rec-photos {{ display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }}
    .rec-photo {{ flex: 1; border-radius: 8px; overflow: hidden; position: relative; }}
    .rec-photo img {{ width: 100%; height: 140px; object-fit: cover; display: block; }}
    .toc {{ background: var(--card-bg); border-radius: 12px; padding: 0.8rem 1rem; margin-bottom: 1.5rem; }}
    .mini-toc {{ margin-top: 2rem; }}
    .toc-title {{ font-weight: 600; font-size: 0.9rem; color: var(--text); margin-bottom: 0.5rem; }}
    .toc-act {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.5rem; font-weight: 600; }}
    .toc-scene {{ display: block; font-size: 0.8rem; color: var(--accent); text-decoration: none; padding: 0.15rem 0 0.15rem 0.8rem; }}
    .toc-scene:hover {{ opacity: 0.7; }}
    .act-heading {{ color: var(--accent); font-size: 1.1rem; margin: 1.5rem 0 0.5rem; padding-bottom: 0.3rem; border-bottom: 1px solid var(--divider); }}
    .scene-card {{ background: var(--card-bg); border-radius: 12px; padding: 1rem; margin-bottom: 0.75rem; }}
    .scene-header {{ display: flex; align-items: flex-start; gap: 0.75rem; }}
    .scene-num {{ font-size: 1.4rem; font-weight: 700; color: var(--accent); min-width: 1.8rem; text-align: center; line-height: 1.2; }}
    .scene-info {{ flex: 1; min-width: 0; }}
    .scene-title {{ font-size: 1rem; font-weight: 600; }}
    .scene-meta {{ font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.15rem; }}
    .scene-chars {{ font-size: 0.75rem; color: var(--text-secondary); font-style: italic; margin-top: 0.1rem; }}
    .ytm-btn {{ display: flex; align-items: center; justify-content: center; width: 2.4rem; height: 2.4rem; border-radius: 50%; background: #FF0000; color: #fff; text-decoration: none; font-size: 1rem; flex-shrink: 0; margin-top: 0.2rem; }}
    .ytm-btn:hover {{ opacity: 0.85; }}
    .scene-img {{ margin: 0.6rem 0 0; border-radius: 8px; overflow: hidden; position: relative; }}
    .scene-img img {{ width: 100%; height: auto; display: block; opacity: 0.85; }}
    .scene-img.atmos img {{ height: 160px; object-fit: cover; opacity: 0.7; }}
    .img-credit {{ position: absolute; bottom: 0; right: 0; background: rgba(0,0,0,0.7); color: #aaa; font-size: 0.65rem; padding: 0.15rem 0.4rem; border-radius: 8px 0 0 0; }}
    .perf-photo {{ float: right; width: 80px; height: 100px; object-fit: cover; border-radius: 6px; margin: 0 0 0.4rem 0.6rem; opacity: 0.9; }}
    .performers-content {{ font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; margin: 0.3rem 0 0; overflow: hidden; }}
    .scene-synopsis {{ font-size: 0.85rem; line-height: 1.55; margin: 0.6rem 0 0.3rem; color: var(--text); }}
    .scene-quote {{ margin: 0.4rem 0; padding: 0.4rem 0.8rem; border-left: 3px solid var(--accent); font-style: italic; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.4; }}
    .scene-details {{ margin-top: 0.3rem; }}
    .scene-details summary {{ font-size: 0.8rem; color: var(--accent); cursor: pointer; padding: 0.2rem 0; }}
    .scene-details p {{ font-size: 0.8rem; color: var(--text-secondary); line-height: 1.5; margin: 0.3rem 0 0; }}
    .footer {{ text-align: center; color: var(--text-secondary); font-size: 0.75rem; margin: 2rem 0 1rem; }}
    .footer a {{ color: var(--accent); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Gotterdammerung on the Go</h1>
    <div class="subtitle">Scene-by-scene listening guide &middot; 12 playlists &middot; 69 tracks</div>
    <div class="recording-info">
      <div class="rec-photos">
        <div class="rec-photo"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Festspielhaus_Bayreuth_001.jpg/400px-Festspielhaus_Bayreuth_001.jpg" alt="Bayreuth Festspielhaus" loading="lazy"><span class="img-credit">DALIBRI, CC BY-SA 4.0</span></div>
        <div class="rec-photo"><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Daniel_Barenboim_%40_Staatsoper_f%C3%BCr_alle_2014_cropped.jpg/300px-Daniel_Barenboim_%40_Staatsoper_f%C3%BCr_alle_2014_cropped.jpg" alt="Daniel Barenboim" loading="lazy"><span class="img-credit">Sebaso, CC BY-SA 3.0</span></div>
      </div>
      <strong>The Recording:</strong> Daniel Barenboim conducting the Bayreuth Festival Orchestra, 1991. Staged by Harry Kupfer. Recorded live in the Festspielhaus (above left), the theatre Wagner designed specifically for his operas — the orchestra plays from a covered pit, invisible to the audience, producing a uniquely blended sound.
      <br><br>
      <strong>Bayreuth</strong> is a small Franconian town in northern Bavaria where Wagner built his Festspielhaus in 1876. The annual festival draws audiences from around the world, with waiting lists stretching years. This recording captures one of the great modern Ring cycles — Barenboim\'s brisk tempi emphasise forward drama over lingering Romanticism.
      <br><br>
      <a href="https://music.youtube.com/playlist?list=OLAK5uy_k-904jYLqH1bXAkGMbdNvMJPL9zbKbCsM" target="_blank">Full album on YouTube Music</a> &middot; Total duration: approx. 4 hours 20 minutes
    </div>
{toc_html}
{cards_html}
    <div class="footer">
      Artwork: Arthur Rackham (1910-11), public domain. Performer/venue photos: Wikimedia Commons (CC BY-SA). Atmosphere photos: Peter Grecian.<br>
      <a href="/contents">Home</a>
    </div>
  </div>
<script>
(function(){{
  var creditsOn=localStorage.getItem('gotg-credits')!=='off';
  function apply(){{document.querySelectorAll('.img-credit').forEach(function(el){{el.style.display=creditsOn?'':'none';}});}}
  apply();
  var mo=new MutationObserver(apply);
  mo.observe(document.body,{{childList:true,subtree:true}});
  function addMenuItem(){{
    var menu=window._settingsMenu;
    if(!menu)return;
    var item=document.createElement('div');
    item.className='settings-item';
    var label=document.createElement('span');
    label.textContent='Photo credits';
    var check=document.createElement('span');
    check.className='check';
    function upd(){{check.textContent=creditsOn?'\u2713':'';}}
    upd();
    item.appendChild(label);
    item.appendChild(check);
    item.onclick=function(e){{
      e.stopPropagation();
      creditsOn=!creditsOn;
      localStorage.setItem('gotg-credits',creditsOn?'on':'off');
      upd();apply();
    }};
    menu.appendChild(item);
  }}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',addMenuItem);
  else addMenuItem();
}})();
</script>
</body>
</html>'''


