// Checking off ingredients, and cook mode: one step at a time, read aloud,
// with "next", "back" and the like said out loud when the mic is on.
(function () {
  const list = document.getElementById("ingredient-list");
  if (!list) return;

  function getPref(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value === null ? fallback : value === "1";
    } catch (e) {
      return fallback;
    }
  }

  function setPref(key, on) {
    try {
      localStorage.setItem(key, on ? "1" : "0");
    } catch (e) {
      /* ignore */
    }
  }

  // --- Checking off ingredients ---
  // Kept on this device for a while, so a reload halfway through doesn't lose
  // them, but the next time you make the recipe starts with none checked.
  const CHECK_KEY = `recipes.checked.${list.dataset.recipeId}`;
  const CHECK_KEEP_MS = 12 * 60 * 60 * 1000;
  const clearChecks = document.getElementById("ing-check-clear");
  let checked = new Set();

  try {
    const saved = JSON.parse(localStorage.getItem(CHECK_KEY));
    if (saved && Date.now() - saved.at < CHECK_KEEP_MS) checked = new Set(saved.items);
  } catch (e) {
    /* nothing saved */
  }

  function saveChecks() {
    try {
      if (checked.size) localStorage.setItem(CHECK_KEY, JSON.stringify({ at: Date.now(), items: [...checked] }));
      else localStorage.removeItem(CHECK_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  // Paints both the page's list and cook mode's copy of it.
  function paintChecks() {
    document.querySelectorAll(".ingredient-item[data-ing-index]").forEach((row) => {
      const on = checked.has(row.dataset.ingIndex);
      row.classList.toggle("is-checked", on);
      const box = row.querySelector(".ing-check");
      if (box) box.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (clearChecks) clearChecks.hidden = checked.size === 0;
  }

  // The whole row checks off (an easy target with floury fingers), except the
  // shopping list button.
  document.addEventListener("click", (e) => {
    const row = e.target.closest(".ingredient-item[data-ing-index]");
    if (!row || e.target.closest(".shop-btn")) return;
    const index = row.dataset.ingIndex;
    if (checked.has(index)) checked.delete(index);
    else checked.add(index);
    saveChecks();
    paintChecks();
  });

  if (clearChecks) {
    clearChecks.querySelector("button").addEventListener("click", () => {
      checked.clear();
      saveChecks();
      paintChecks();
    });
  }
  paintChecks();

  // --- Cook mode ---
  const cook = document.getElementById("cook");
  const stepsData = document.getElementById("cook-steps");
  if (!cook || !stepsData) return;

  const steps = JSON.parse(stepsData.textContent);
  const stepEl = document.getElementById("cook-step");
  const doneEl = document.getElementById("cook-done");
  const countEl = document.getElementById("cook-count");
  const progressEl = document.getElementById("cook-progress");
  const heardEl = document.getElementById("cook-heard");
  const prevBtn = document.getElementById("cook-prev");
  const nextBtn = document.getElementById("cook-next");
  const ingBtn = document.getElementById("cook-ing-btn");
  const ingPanel = document.getElementById("cook-ingredients");
  const ingList = document.getElementById("cook-ingredient-list");
  const speakBtn = document.getElementById("cook-speak");
  const micBtn = document.getElementById("cook-mic");
  const SPEAK_KEY = "recipes.cook.speak";
  const LISTEN_KEY = "recipes.cook.listen";
  const HINT = "Listening: say “next”, “back”, “repeat” or “ingredients”.";

  // 0 … steps.length - 1 are the steps; steps.length is the "All done" page.
  let index = 0;
  let opener = null;

  function show(i) {
    index = Math.max(0, Math.min(i, steps.length));
    const done = index === steps.length;
    stepEl.hidden = done;
    doneEl.hidden = !done;
    if (!done) stepEl.textContent = steps[index];
    countEl.textContent = done ? "All done" : `Step ${index + 1} of ${steps.length}`;
    progressEl.style.width = `${(Math.min(index + 1, steps.length) / steps.length) * 100}%`;
    prevBtn.disabled = index === 0;
    nextBtn.disabled = done;
    readCurrent();
  }

  function readCurrent() {
    if (index === steps.length) speak("All done. Enjoy!");
    else speak(`Step ${index + 1}. ${steps[index]}`);
  }

  function next() {
    show(index + 1);
  }

  function prev() {
    show(index - 1);
  }

  // Cook mode's ingredient list is copied from the page's each time it opens,
  // so it shows the amounts the scale slider is set to.
  function toggleIngredients(open) {
    const want = typeof open === "boolean" ? open : ingPanel.hidden;
    if (want) {
      ingList.replaceChildren();
      list.querySelectorAll("[data-ing-index]").forEach((row) => {
        const li = document.createElement("li");
        if (row.classList.contains("ingredient-heading")) {
          li.className = "ingredient-heading";
          li.textContent = row.textContent.trim();
        } else {
          li.className = "ingredient-item";
          li.dataset.ingIndex = row.dataset.ingIndex;
          const text = document.createElement("span");
          text.className = "ingredient-item-main";
          text.textContent = row.querySelector(".ingredient-item-text").textContent;
          li.append(row.querySelector(".ing-check").cloneNode(true), text);
        }
        ingList.append(li);
      });
      paintChecks();
    }
    ingPanel.hidden = !want;
    cook.classList.toggle("cook--ingredients", want);
    ingBtn.setAttribute("aria-expanded", want ? "true" : "false");
    ingBtn.textContent = want ? "Steps" : "Ingredients";
  }

  // Opening cook mode adds a history entry, so the phone's back gesture
  // closes it instead of leaving the recipe.
  function openCook() {
    if (!cook.hidden) return;
    opener = document.activeElement;
    cook.hidden = false;
    document.body.classList.add("cook-open");
    history.pushState({ cook: true }, "");
    toggleIngredients(false);
    show(index);
    keepAwake();
    paintListening();
    startListening();
    nextBtn.focus();
  }

  function closeCook() {
    if (history.state && history.state.cook) history.back();
    else hideCook();
  }

  function hideCook() {
    if (cook.hidden) return;
    cook.hidden = true;
    document.body.classList.remove("cook-open");
    stopSpeaking();
    stopListening();
    letSleep();
    if (opener) opener.focus();
  }

  window.addEventListener("popstate", hideCook);
  // A reload while cook mode was open leaves its history entry behind.
  if (history.state && history.state.cook) history.replaceState(null, "");
  document.querySelectorAll("[data-cook-start]").forEach((btn) => btn.addEventListener("click", openCook));
  document.getElementById("cook-close").addEventListener("click", closeCook);
  prevBtn.addEventListener("click", prev);
  nextBtn.addEventListener("click", next);
  ingBtn.addEventListener("click", () => toggleIngredients());

  cook.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeCook();
    else if (e.key === "ArrowRight") next();
    else if (e.key === "ArrowLeft") prev();
    else return;
    e.preventDefault();
  });

  // Swipe left for the next step, right for the one before.
  let touchStart = null;
  const main = cook.querySelector(".cook-main");
  main.addEventListener("touchstart", (e) => {
    touchStart = e.touches.length === 1 ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null;
  }, { passive: true });
  main.addEventListener("touchend", (e) => {
    if (!touchStart) return;
    const dx = e.changedTouches[0].clientX - touchStart.x;
    const dy = e.changedTouches[0].clientY - touchStart.y;
    touchStart = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      if (dx < 0) next();
      else prev();
    }
  });

  // --- Keeping the screen on (needs https, so not on the plain-http address) ---
  let wakeLock = null;

  function keepAwake() {
    if (!("wakeLock" in navigator) || cook.hidden) return;
    navigator.wakeLock.request("screen").then((lock) => {
      wakeLock = lock;
    }, () => {
      /* not allowed here; the screen sleeps as usual */
    });
  }

  function letSleep() {
    if (wakeLock) wakeLock.release();
    wakeLock = null;
  }

  // The lock lapses when you switch apps, and the mic stops listening.
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible" || cook.hidden) return;
    keepAwake();
    startListening();
  });

  // --- Reading aloud ---
  const synth = window.speechSynthesis;
  let speakOn = Boolean(synth) && getPref(SPEAK_KEY, true);
  let speaking = false;
  let utterance = null; // held so Chrome doesn't drop it before it ends

  if (!synth) speakBtn.hidden = true;

  function paintSpeaking() {
    speakBtn.setAttribute("aria-pressed", speakOn ? "true" : "false");
    speakBtn.setAttribute("aria-label", speakOn ? "Stop reading steps aloud" : "Read steps aloud");
  }

  function speak(text) {
    if (!synth || !speakOn || cook.hidden) return;
    synth.cancel();
    utterance = new SpeechSynthesisUtterance(spokenText(text));
    utterance.lang = document.documentElement.lang || "en";
    // A little slower than normal, for following along at the stove.
    utterance.rate = 0.9;
    const mine = utterance;
    mine.onend = mine.onerror = () => {
      if (utterance !== mine) return;
      speaking = false;
      startListening();
    };
    // The mic would hear the step being read and act on it, so it stops
    // listening until the reading ends.
    speaking = true;
    stopListening();
    synth.speak(mine);
  }

  function stopSpeaking() {
    utterance = null;
    speaking = false;
    if (synth) synth.cancel();
  }

  // Safari sometimes skips the "end" event, which would leave the mic off.
  setInterval(() => {
    if (speaking && synth && !synth.speaking && !synth.pending) {
      speaking = false;
      startListening();
    }
  }, 1000);

  speakBtn.addEventListener("click", () => {
    speakOn = !speakOn;
    setPref(SPEAK_KEY, speakOn);
    paintSpeaking();
    if (speakOn) readCurrent();
    else {
      stopSpeaking();
      startListening();
    }
  });
  paintSpeaking();

  // --- Listening for commands (Safari and Chrome, over https) ---
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const canListen = Boolean(Recognition) && window.isSecureContext;
  let listenOn = canListen && getPref(LISTEN_KEY, false);
  let recognizer = null;
  let startedAt = 0;
  let quickEnds = 0;
  let heardTimer = null;

  micBtn.hidden = !canListen;

  // Checked in order, so "go back" isn't taken for something else.
  const COMMANDS = [
    [/\b(start over|from the top|first step)\b/, () => show(0)],
    [/\b(back|previous|last step)\b/, prev],
    [/\b(next|forward|continue|go on)\b/, next],
    [/\b(repeat|again|what)\b/, readCurrent],
    [/\bingredients?\b/, () => toggleIngredients()],
    [/\b(steps?|instructions)\b/, () => toggleIngredients(false)],
    [/\b(stop|quiet|hush|pause)\b/, () => {
      stopSpeaking();
      startListening();
    }],
    [/\b(close|exit)\b/, closeCook],
  ];

  function paintListening(message) {
    micBtn.setAttribute("aria-pressed", listenOn ? "true" : "false");
    micBtn.setAttribute("aria-label", listenOn ? "Stop listening" : "Listen for voice commands");
    clearTimeout(heardTimer);
    heardEl.hidden = !listenOn && !message;
    heardEl.textContent = message || HINT;
    if (message && listenOn) heardTimer = setTimeout(() => paintListening(), 2500);
  }

  function startListening() {
    if (!listenOn || recognizer || speaking || cook.hidden || document.visibilityState !== "visible") return;
    // One phrase at a time: Safari on iPhone is more dependable that way
    // than with continuous listening, so it starts again after each one.
    const rec = new Recognition();
    rec.lang = document.documentElement.lang || "en";
    rec.continuous = false;
    rec.interimResults = false;
    rec.maxAlternatives = 3;
    rec.onresult = (e) => {
      const alternatives = Array.from(e.results[e.results.length - 1]).map((a) => a.transcript.toLowerCase().replace(/[.,!?]/g, "").trim());
      heard(alternatives);
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        listenOn = false;
        setPref(LISTEN_KEY, false);
        paintListening("The microphone isn't allowed for this site. You can allow it in your browser's settings.");
      }
    };
    rec.onend = () => {
      if (recognizer !== rec) return;
      recognizer = null;
      // A browser that won't listen ends straight away every time; give up
      // rather than spin.
      quickEnds = Date.now() - startedAt < 1500 ? quickEnds + 1 : 0;
      if (quickEnds >= 5) {
        listenOn = false;
        paintListening("Listening stopped working. Tap the microphone to try again.");
        return;
      }
      setTimeout(startListening, 250);
    };
    recognizer = rec;
    startedAt = Date.now();
    try {
      rec.start();
    } catch (e) {
      recognizer = null;
    }
  }

  function stopListening() {
    const rec = recognizer;
    recognizer = null;
    if (rec) rec.abort();
  }

  // Commands are short, so anything longer is people talking in the kitchen.
  function heard(alternatives) {
    for (const said of alternatives) {
      if (said.split(/\s+/).length > 4) continue;
      const command = COMMANDS.find(([pattern]) => pattern.test(said));
      if (command) {
        paintListening(`Heard “${said}”`);
        command[1]();
        return;
      }
    }
  }

  micBtn.addEventListener("click", () => {
    listenOn = !listenOn;
    quickEnds = 0;
    setPref(LISTEN_KEY, listenOn);
    paintListening();
    if (listenOn) startListening();
    else stopListening();
  });

  // --- Recipe text tidied for reading aloud, as on the TV ---
  const FRACTION_WORDS = {
    "½": "a half",
    "⅓": "a third",
    "⅔": "two thirds",
    "¼": "a quarter",
    "¾": "three quarters",
    "⅛": "an eighth",
  };

  // "1 ½ cups" becomes "1 and a half cups", "2-3" becomes "2 to 3",
  // 2"x3" becomes "2 by 3 inches" and 350°F becomes "350 degrees".
  function spokenText(text) {
    let s = text.replace(/\n/g, " ");
    s = s.replace(/(\d)\s*([½⅓⅔¼¾⅛])/g, (m, whole, f) => `${whole} and ${FRACTION_WORDS[f]}`);
    s = s.replace(/[½⅓⅔¼¾⅛]/g, (f) => FRACTION_WORDS[f]);
    s = s.replace(/(\d)\s*[-–]\s*(\d)/g, "$1 to $2");
    s = s.replace(/(\d)\s*["”]?\s*x\s*(\d)/g, "$1 by $2");
    s = s.replace(/(\d)\s*["”]/g, "$1 inches");
    s = s.replace(/(\d)\s*°(\s*F\b)?/g, "$1 degrees");
    return s;
  }
})();
