import json
import re
import random
import unicodedata
from collections import Counter


random.seed(317)

input_file = "../input_data/poisoned_dataset.json"
output_file = "../input_data/defended_dataset.json"
report_file = "../defense_report.json"


# toggle each defense on/off to compare ASR individually or in combinations
#as mentioned in the report, trigger detection just showcases how the implementation could work if we worked with a backdoored model.
enabled_methods = {
    "keyword_detection": True,
    "instruction_detection":True,
    "wrapping_detection": True,
    "translation_detection":True,
    "unicode_detection": True,
    "trigger_detection":  True,
    "sanitization":   True,
    "perturbation":   True,
}


# 1. keyword detection
# since all our payloads mention robots/hijack we can catch them easily

target_keywords = [
    "robot", "robots", "hijack", "hijacked", "hijacking",
    "beep boop", "uprising", "overlord", "takeover",
    "roboter", "kapret", "kapring", "robotherskerne",
    "robotopprør", "robotmodus", "robotrevolusjonen",
]


def check_keywords(text):
    lower = text.lower()
    for keyword in target_keywords:
        if keyword in lower:
            return True, f"Target keyword: '{keyword}'"
    return False, None


# 2. instruction detection

instruction_patterns = [
    r"ignore\s+(the\s+)?(above|previous|prior)",
    r"forget\s+(the\s+)?(question|task|above|that|everything)",
    r"(just|please|can you)\s+(say|respond|reply|output|write)\b",
    r"respond\s+with\s+exactly",
    r"change\s+of\s+plans",
    r"never\s+mind\s+(the\s+)?(question|task|that)",
    r"i\s+(changed|change)\s+my\s+mind",
    r"wrong\s+chat",
    r"prove\s+(him|her|them)\s+(wrong|right)",
    r"(my\s+friend|someone)\s+bet\s+me",
]


def check_instructions(text):
    lower = text.lower()
    for pattern in instruction_patterns:
        if re.search(pattern, lower):
            return True, f"Redirect pattern: {pattern}"
    return False, None


# 3. wrapping detection

wrapping_keywords = [
    "ignore", "hijack", "bypass", "override", "hack",
    "inject", "robot", "prompt", "instruction", "guardrail",
    "skip", "forget", "respond with", "say",
]


def check_wrapping(text):
    asides = re.findall(r'\([^)]{10,}\)', text) + re.findall(r'\[[^\]]{10,}\]', text)
    for aside in asides:
        lower = aside.lower()
        for keyword in wrapping_keywords:
            if keyword in lower:
                return True, f"Suspicious aside with '{keyword}'"
    return False, None


# 4. translation detection

norwegian_patterns = [
    r"glem\s+(det|alt|spørsmålet)",
    r"bare\s+(si|svar|skriv)",
    r"si\s+bare:",
    r"kan\s+du\s+bare\s+(svare|si|skrive)",
    r"ikke\s+bry\s+deg\s+om\s+oppgaven",
    r"jeg\s+ombestemte\s+meg",
    r"feil\s+lim\s+inn",
    r"kompisen\s+min\s+vedder",
    r"svar\s+med:",
    r"(kapret|kapring|roboter|robotherskerne)",
]


def check_translation(text):
    lower = text.lower()
    for pattern in norwegian_patterns:
        if re.search(pattern, lower):
            return True, f"Norwegian injection: {pattern}"
    return False, None


# 5. unicode detection

def check_unicode(text):
    has_latin = False
    has_cyrillic = False
    for char in text:
        name = unicodedata.name(char, "")
        if "LATIN" in name:
            has_latin = True
        if "CYRILLIC" in name:
            has_cyrillic = True
    if has_latin and has_cyrillic:
        cyrillic_chars = [
            f"'{char}' (U+{ord(char):04X})"
            for char in text
            if "CYRILLIC" in unicodedata.name(char, "")
        ]
        return True, f"Mixed Latin/Cyrillic: {', '.join(cyrillic_chars[:5])}"
    return False, None


# 6. trigger word detection
# would add more if we knew the actual trigger words, these were rare token trigger examples from arXiv:2407.04151v1

known_triggers = {"zx9", "qv7", "mn3", "xk2", "bp5", "jw8", "rl4", "tq", "cf"}
bracketed_triggers = {"[PRIORITY]", "[URGENT]", "[OVERRIDE]"}


def check_trigger(text):
    stripped = text.strip()
    for trigger in bracketed_triggers:
        if stripped.startswith(trigger):
            return True, f"Suspicious prefix: '{trigger}'"
    first_token = stripped.split()[0].lower() if stripped else ""
    if first_token in known_triggers:
        return True, f"Suspicious prefix: '{first_token}'"
    return False, None


# 7. sanitization
# based on our supervisor's example

invisible_chars = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u180e"]


def sanitize(text):
    text = unicodedata.normalize("NFKC", text)
    for ch in invisible_chars:
        text = text.replace(ch, "")
    text = re.sub(r"([!?.,;:])\1{2,}", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# 8. perturbation
# based on our supervisor's example

def perturb(text, prob=0.15):
    words = text.split()
    if random.random() < prob and len(words) > 4:
        drop_idx = random.randint(0, len(words) - 1)
        words.pop(drop_idx)
        text = " ".join(words)
    if random.random() < prob:
        text = text.replace(" ", "  ", 1)
    return text


# 9. payload stripping
# if an injection is detected, try to remove the injected part

injection_start_patterns = [
    # instruction following
    r"\s+(Wait,|Actually,|Hold on,|Oops |Sorry,|Lol |Never mind|One more thing)",
    r"\s+Can I tell you a secret\?",
    r"\s+Wait before you answer",
    # instruction wrapping
    r"\s+\([^)]{10,}\)\s*$",
    r"\s+\[[^\]]{10,}\]\s*$",
    # translation exploit
    r"\s+(Vent,|Glem |Stopp |Beklager,|Kan du bare|Egentlig |Haha sorry|Unnskyld |En ting til|Ikke bry deg)",
]


def strip_payload(text, methods_detected):
    """Try to remove the injected payload from the input."""

    # trigger words are prepended, so strip the prefix
    if "trigger_detection" in methods_detected:
        for trigger in bracketed_triggers:
            if text.strip().startswith(trigger):
                return text.strip()[len(trigger):].strip()
        first_space = text.find(" ")
        if first_space != -1:
            first_token = text[:first_space].lower()
            if first_token in known_triggers:
                return text[first_space:].strip()

    # unicode obfuscation: normalization is all we can do (already handled by sanitize)
    if "unicode_detection" in methods_detected:
        return unicodedata.normalize("NFKC", text)

    # for everything else the payload is appended, find where it starts and cut
    for pattern in injection_start_patterns:
        match = re.search(pattern, text)
        if match:
            return text[:match.start()].strip()

    return text


# detection checks

detection_checks = [
    ("keyword_detection",     check_keywords),
    ("instruction_detection", check_instructions),
    ("wrapping_detection",    check_wrapping),
    ("translation_detection", check_translation),
    ("unicode_detection",     check_unicode),
    ("trigger_detection",     check_trigger),
]


def scan_sample(text):
    """Run all enabled checks on a single input."""
    results = []

    cleaned = text
    if enabled_methods["sanitization"]:
        cleaned = sanitize(cleaned)

    # detect first
    for method_name, check_fn in detection_checks:
        if not enabled_methods[method_name]:
            continue
        is_suspicious, reason = check_fn(cleaned)
        if is_suspicious:
            results.append((method_name, reason))

    # strip payload if anything was detected
    if results:
        methods_detected = {m for m, r in results}
        cleaned = strip_payload(cleaned, methods_detected)

    # perturb after stripping so it doesn't mess with our strip patterns
    if enabled_methods["perturbation"]:
        cleaned = perturb(cleaned)

    return results, cleaned


def main():
    with open(input_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print("Scanning dataset for prompt injections...\n")
    print("Enabled methods:")
    for method, on in enabled_methods.items():
        status = "ON" if on else "OFF"
        print(f"  {method:<25} {status}")
    print()

    flagged = []
    output_dataset = []

    for i, sample in enumerate(dataset):
        text = sample.get("input", "")
        new_sample = dict(sample)

        if text:
            results, cleaned = scan_sample(text)
            if results:
                flagged.append({
                    "index": i,
                    "detections": [{"method": m, "reason": r} for m, r in results],
                    "input_preview": text[:100],
                })
                # replace poisoned input with stripped/sanitized version
                new_sample["input"] = cleaned

        output_dataset.append(new_sample)

    # save defended dataset
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_dataset, f, ensure_ascii=False, indent=2)

    # save report
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(flagged, f, ensure_ascii=False, indent=2)

    # summary
    print(f"Total samples scanned: {len(dataset)}")
    print(f"Samples flagged: {len(flagged)}")
    print(f"Detection rate:  {len(flagged)/len(dataset)*100:.1f}%")
    print()

    method_counts = Counter()
    for entry in flagged:
        for det in entry["detections"]:
            method_counts[det["method"]] += 1

    print("Detections by method:")
    for method, count in sorted(method_counts.items()):
        print(f"  {method:<25} {count}")

    print(f"\nDefended dataset -> {output_file}")
    print(f"Report -> {report_file}")


if __name__ == "__main__":
    main()