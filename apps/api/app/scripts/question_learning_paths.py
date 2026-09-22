"""Bilingual, author-curated walkthroughs for Codele's starter library.

Trace state intentionally uses JSON primitives so the same sequence can be
rendered by the web player without executing learner or reference code.
"""

# Long translated prose and compact JSON trace states are data, not executable
# logic; keeping each item on one line makes the authored walkthroughs readable.
# ruff: noqa: E501

LEARNING_PATHS: dict[str, dict[str, object]] = {
    "add-two-values": {
        "en": "Read both values, add them once, and return the computed sum. No loop or extra storage is needed.",
        "ml": "രണ്ട് മൂല്യങ്ങളും വായിച്ച് ഒരിക്കൽ കൂട്ടി ഫലം മടക്കുക. ലൂപ്പോ അധിക സംഭരണമോ ആവശ്യമില്ല.",
        "trace": [
            {"step": 1, "state": {"a": 3, "b": 8}, "note": "Read the two inputs."},
            {"step": 2, "state": {"expression": "3 + 8", "sum": 11}, "note": "Evaluate the addition."},
            {"step": 3, "state": {"return": 11}, "note": "Return the sum."},
        ],
        "notes_en": ["Read both inputs.", "Evaluate the addition.", "Return the sum."],
        "notes_ml": ["രണ്ട് ഇൻപുട്ടുകളും വായിക്കുക.", "കൂട്ടൽ കണക്കാക്കുക.", "തുക മടക്കുക."],
    },
    "mirror-a-message": {
        "en": "Walk from the end of the text toward the beginning, or use the language's reverse operation, to build the mirrored message.",
        "ml": "ടെക്സ്റ്റിന്റെ അവസാനത്തിൽ നിന്ന് തുടക്കത്തിലേക്ക് സഞ്ചരിക്കുകയോ ഭാഷയുടെ reverse പ്രവർത്തനം ഉപയോഗിക്കുകയോ ചെയ്ത് മറിച്ച സന്ദേശം നിർമ്മിക്കുക.",
        "trace": [
            {"step": 1, "state": {"text": "code", "cursor": 3}, "note": "Start at the last character."},
            {"step": 2, "state": {"result": "ed", "cursor": 1}, "note": "Append characters while moving left."},
            {"step": 3, "state": {"return": "edoc"}, "note": "The reversed text is complete."},
        ],
        "notes_en": ["Start at the last character.", "Append while moving left.", "Return the reversed text."],
        "notes_ml": ["അവസാന അക്ഷരത്തിൽ നിന്ന് തുടങ്ങുക.", "ഇടത്തേക്ക് നീങ്ങുമ്പോൾ അക്ഷരങ്ങൾ ചേർക്കുക.", "മറിച്ച ടെക്സ്റ്റ് മടക്കുക."],
    },
    "count-the-vowels": {
        "en": "Normalize each character to one case, then increment a counter whenever it belongs to the five-vowel set.",
        "ml": "ഓരോ അക്ഷരവും ഒരേ case-ലേക്ക് മാറ്റി, അഞ്ച് സ്വരാക്ഷരങ്ങളുടെ സെറ്റിൽ ഉണ്ടെങ്കിൽ കൗണ്ടർ വർധിപ്പിക്കുക.",
        "trace": [
            {"step": 1, "state": {"text": "Codele", "vowels": "aeiou", "count": 0}, "note": "Prepare the vowel lookup."},
            {"step": 2, "state": {"character": "o", "normalized": "o", "count": 1}, "note": "Count a matching vowel."},
            {"step": 3, "state": {"return": 3}, "note": "Return the final count."},
        ],
        "notes_en": ["Prepare the lookup.", "Count each matching vowel.", "Return the count."],
        "notes_ml": ["തിരയാനുള്ള സെറ്റ് തയ്യാറാക്കുക.", "ഓരോ പൊരുത്തപ്പെടുന്ന സ്വരാക്ഷരവും എണ്ണുക.", "ആകെ എണ്ണം മടക്കുക."],
    },
    "bracket-check": {
        "en": "Push opening brackets onto a stack. For each closing bracket, it must match the most recent opening bracket. The stack must finish empty.",
        "ml": "തുറക്കുന്ന ബ്രാക്കറ്റുകൾ stack-ലേക്ക് ചേർക്കുക. ഓരോ അടയ്ക്കുന്ന ബ്രാക്കറ്റും ഏറ്റവും പുതിയ തുറക്കുന്ന ബ്രാക്കറ്റിനോട് പൊരുത്തപ്പെടണം. അവസാനം stack ശൂന്യമായിരിക്കണം.",
        "trace": [
            {"step": 1, "state": {"character": "{", "stack": ["{"]}, "note": "Push an opening bracket."},
            {"step": 2, "state": {"character": ")", "stack_before": ["{", "[", "("], "stack_after": ["{", "["]}, "note": "Match and pop the latest opening bracket."},
            {"step": 3, "state": {"stack": [], "return": True}, "note": "An empty stack means balanced brackets."},
        ],
        "notes_en": ["Push an opener.", "Match and pop its closer.", "Empty stack means balanced."],
        "notes_ml": ["തുറക്കുന്ന ചിഹ്നം push ചെയ്യുക.", "അടയ്ക്കുന്ന ചിഹ്നവുമായി പൊരുത്തപ്പെടുത്തി pop ചെയ്യുക.", "ശൂന്യമായ stack എന്നത് ബാലൻസ്ഡ് ആണെന്ന് അർത്ഥം."],
    },
    "find-in-sorted-list": {
        "en": "Binary search compares the target with the middle item and discards the half that cannot contain it, until it is found or the interval is empty.",
        "ml": "Binary search target-നെ നടുവിലെ മൂല്യവുമായി താരതമ്യം ചെയ്ത് അതില്ലാത്ത പകുതി ഒഴിവാക്കുന്നു; കണ്ടെത്തുന്നതോ പരിധി ശൂന്യമാകുന്നതോ വരെ ഇത് തുടരുന്നു.",
        "trace": [
            {"step": 1, "state": {"values": [1, 4, 7, 10, 15], "left": 0, "right": 4, "target": 10}, "note": "Search the full sorted interval."},
            {"step": 2, "state": {"middle": 2, "value": 7, "decision": "move left to 3"}, "note": "The target is larger, so discard the left half."},
            {"step": 3, "state": {"middle": 3, "value": 10, "return": 3}, "note": "The middle item matches the target."},
        ],
        "notes_en": ["Search the whole interval.", "Discard the impossible half.", "Return the matching index."],
        "notes_ml": ["മുഴുവൻ sorted പരിധിയും പരിശോധിക്കുക.", "സാധ്യതയില്ലാത്ത പകുതി ഒഴിവാക്കുക.", "പൊരുത്തപ്പെടുന്ന index മടക്കുക."],
    },
    "first-lonely-character": {
        "en": "First count every character. Then scan the original order again and return the first index whose count is exactly one.",
        "ml": "ആദ്യം എല്ലാ അക്ഷരങ്ങളും എണ്ണുക. തുടർന്ന് യഥാർത്ഥ ക്രമത്തിൽ വീണ്ടും നോക്കി എണ്ണം ഒന്ന് മാത്രമായ ആദ്യ index മടക്കുക.",
        "trace": [
            {"step": 1, "state": {"text": "swiss", "counts": {"s": 3, "w": 1, "i": 1}}, "note": "Build frequency counts."},
            {"step": 2, "state": {"index": 1, "character": "w", "count": 1}, "note": "Scan in the original order."},
            {"step": 3, "state": {"return": 1}, "note": "The first unique character is found."},
        ],
        "notes_en": ["Count all characters.", "Scan in original order.", "Return the first unique index."],
        "notes_ml": ["എല്ലാ അക്ഷരങ്ങളും എണ്ണുക.", "യഥാർത്ഥ ക്രമത്തിൽ പരിശോധിക്കുക.", "ആദ്യ unique index മടക്കുക."],
    },
    "longest-unique-window": {
        "en": "Maintain a window with no duplicates. Remember each character's last index; when a repeat lies inside the window, move the left edge beyond it.",
        "ml": "duplicate ഇല്ലാത്ത ഒരു window നിലനിർത്തുക. ഓരോ അക്ഷരത്തിന്റെയും അവസാന index ഓർക്കുക; ആവർത്തനം window-ലുള്ളതാണെങ്കിൽ left edge അതിന് പിന്നിലേക്ക് മാറ്റുക.",
        "trace": [
            {"step": 1, "state": {"text": "pwwkew", "left": 0, "right": 1, "window": "pw", "best": 2}, "note": "Grow a unique window."},
            {"step": 2, "state": {"character": "w", "previous_index": 1, "left": 2, "window": "w"}, "note": "Move left past the repeated character."},
            {"step": 3, "state": {"window": "wke", "best": 3, "return": 3}, "note": "Record the best window length."},
        ],
        "notes_en": ["Grow the unique window.", "Move left after a repeat.", "Keep the best length."],
        "notes_ml": ["unique window വളർത്തുക.", "ആവർത്തനത്തിന് ശേഷം left മാറ്റുക.", "ഏറ്റവും വലിയ നീളം സൂക്ഷിക്കുക."],
    },
    "combine-time-ranges": {
        "en": "Sort ranges by their start. Compare each range with the last merged range: extend it when they overlap, otherwise start a new range.",
        "ml": "ranges-നെ start അനുസരിച്ച് sort ചെയ്യുക. ഓരോ range-നെയും അവസാനം merge ചെയ്ത range-നോട് താരതമ്യം ചെയ്യുക: overlap ആണെങ്കിൽ നീട്ടുക, അല്ലെങ്കിൽ പുതിയത് തുടങ്ങുക.",
        "trace": [
            {"step": 1, "state": {"sorted_ranges": [[1, 3], [2, 6], [8, 10]], "merged": [[1, 3]]}, "note": "Sort and seed the merged list."},
            {"step": 2, "state": {"current": [2, 6], "overlaps": True, "merged": [[1, 6]]}, "note": "Extend the overlapping range."},
            {"step": 3, "state": {"current": [8, 10], "overlaps": False, "return": [[1, 6], [8, 10]]}, "note": "Append a separate range."},
        ],
        "notes_en": ["Sort ranges first.", "Extend overlaps.", "Append a non-overlapping range."],
        "notes_ml": ["ആദ്യം ranges sort ചെയ്യുക.", "overlap ഉണ്ടെങ്കിൽ നീട്ടുക.", "overlap ഇല്ലാത്ത range ചേർക്കുക."],
    },
    "count-land-clusters": {
        "en": "When an unvisited land cell is found, run DFS or BFS to visit its complete component. Each new traversal contributes one cluster.",
        "ml": "സന്ദർശിക്കാത്ത land cell കണ്ടെത്തുമ്പോൾ DFS അല്ലെങ്കിൽ BFS ഉപയോഗിച്ച് അതിന്റെ മുഴുവൻ component സന്ദർശിക്കുക. ഓരോ പുതിയ traversal-വും ഒരു cluster ആണ്.",
        "trace": [
            {"step": 1, "state": {"cell": [0, 0], "land": True, "clusters": 0}, "note": "Find unvisited land."},
            {"step": 2, "state": {"stack": [[0, 0], [0, 1], [1, 1]], "visited": [[0, 0], [0, 1], [1, 1]], "clusters": 1}, "note": "Visit the whole connected component."},
            {"step": 3, "state": {"clusters": 3, "return": 3}, "note": "Return the number of components."},
        ],
        "notes_en": ["Find unvisited land.", "Traverse its component.", "Count each component once."],
        "notes_ml": ["സന്ദർശിക്കാത്ത land കണ്ടെത്തുക.", "അതിന്റെ component മുഴുവൻ traverse ചെയ്യുക.", "ഓരോ component-ഉം ഒരിക്കൽ എണ്ണുക."],
    },
    "count-coin-combinations": {
        "en": "Use dynamic programming where ways[value] is the number of combinations for that value. Process one coin at a time so different coin orders are not counted twice.",
        "ml": "ways[value] ആ മൂല്യം ഉണ്ടാക്കാനുള്ള combinations-ന്റെ എണ്ണമാണെന്ന dynamic programming ഉപയോഗിക്കുക. വ്യത്യസ്ത coin order-കൾ രണ്ടുതവണ എണ്ണാതിരിക്കാൻ ഒരു സമയം ഒരു coin വീതം process ചെയ്യുക.",
        "trace": [
            {"step": 1, "state": {"amount": 5, "ways": [1, 0, 0, 0, 0, 0]}, "note": "There is one way to make zero."},
            {"step": 2, "state": {"coin": 2, "ways": [1, 1, 2, 2, 3, 3]}, "note": "Update values using the current coin."},
            {"step": 3, "state": {"coin": 5, "ways_at_amount": 4, "return": 4}, "note": "Return the combinations for the target."},
        ],
        "notes_en": ["Seed one way to make zero.", "Update with one coin at a time.", "Return ways at the target."],
        "notes_ml": ["zero ഉണ്ടാക്കാൻ ഒരു വഴി നൽകുക.", "ഒരു സമയം ഒരു coin ഉപയോഗിച്ച് update ചെയ്യുക.", "target-ലെ ways മടക്കുക."],
    },
}


# These are the teaching sentences displayed below the shared player. They
# explain the algorithmic decision, rather than merely describing a variable.
TRACE_NOTES: dict[str, dict[str, list[str]]] = {
    "add-two-values": {
        "en": [
            "We receive two numbers: 3 and 8. There is no list to scan, so we can solve this immediately.",
            "Add the two inputs once: 3 + 8 becomes 11.",
            "Return 11. That returned value is the answer for this test case.",
        ],
        "ml": [
            "നമുക്ക് 3, 8 എന്ന രണ്ട് സംഖ്യകൾ ലഭിക്കുന്നു. പരിശോധിക്കാനുള്ള ലിസ്റ്റില്ല, അതിനാൽ ഉടൻ പരിഹരിക്കാം.",
            "രണ്ട് ഇൻപുട്ടുകളും ഒരിക്കൽ കൂട്ടുക: 3 + 8 = 11.",
            "11 മടക്കുക. ഈ test case-ന്റെ ഉത്തരമാണത്.",
        ],
    },
    "mirror-a-message": {
        "en": [
            "Start at the last character, because the last character becomes the first character in the answer.",
            "Move the cursor left and keep adding the characters you visit to the result.",
            "After every character is visited, the collected text is the reversed message.",
        ],
        "ml": [
            "അവസാന അക്ഷരത്തിൽ നിന്ന് തുടങ്ങുക; അത് ഉത്തരത്തിലെ ആദ്യ അക്ഷരമാകും.",
            "cursor ഇടത്തേക്ക് നീക്കി കാണുന്ന അക്ഷരങ്ങൾ result-ലേക്ക് ചേർക്കുക.",
            "എല്ലാ അക്ഷരങ്ങളും കണ്ടുകഴിഞ്ഞാൽ ശേഖരിച്ച ടെക്സ്റ്റ് മറിച്ച സന്ദേശമാണ്.",
        ],
    },
    "count-the-vowels": {
        "en": [
            "Read the word one character at a time. The counter starts at 0 because we have not found a vowel yet.",
            "The cursor is on “o”. It is in a, e, i, o, u, so increase the counter by one.",
            "Continue the same check for every character. For “Codele”, three characters are vowels, so return 3.",
        ],
        "ml": [
            "വാക്കിലെ ഓരോ അക്ഷരവും ഒന്നൊന്നായി വായിക്കുക. ഇതുവരെ സ്വരാക്ഷരം കണ്ടിട്ടില്ലാത്തതിനാൽ counter 0-ൽ തുടങ്ങുന്നു.",
            "cursor “o” യിലാണ്. അത് a, e, i, o, u-ൽ ഉള്ളതിനാൽ counter ഒന്ന് വർധിപ്പിക്കുക.",
            "എല്ലാ അക്ഷരങ്ങൾക്കും ഇതേ പരിശോധന തുടരുക. “Codele”-ൽ മൂന്ന് സ്വരാക്ഷരങ്ങളുണ്ട്; അതിനാൽ 3 മടക്കുക.",
        ],
    },
    "bracket-check": {
        "en": [
            "When we see an opening bracket, push it onto the stack so we remember that it still needs a matching close.",
            "When we see a closing bracket, compare it with the most recent opening bracket—the top of the stack—and remove the match.",
            "The stack is empty at the end, which proves every opening bracket had the correct closing bracket.",
        ],
        "ml": [
            "തുറക്കുന്ന bracket കണ്ടാൽ അതിന്റെ അടയ്ക്കുന്ന bracket പിന്നീട് പരിശോധിക്കാൻ stack-ലേക്ക് push ചെയ്യുക.",
            "അടയ്ക്കുന്ന bracket കണ്ടാൽ stack-ന്റെ മുകളിലുള്ള ഏറ്റവും പുതിയ തുറക്കുന്ന bracket-നോട് താരതമ്യം ചെയ്ത് match ആണെങ്കിൽ remove ചെയ്യുക.",
            "അവസാനം stack ശൂന്യമാണ്; ഓരോ തുറക്കുന്ന bracket-നും ശരിയായ അടയ്ക്കൽ ലഭിച്ചു എന്ന് അതിനർത്ഥം.",
        ],
    },
    "find-in-sorted-list": {
        "en": [
            "The values are sorted, so begin with the whole range and inspect the middle instead of checking every item.",
            "The middle value is 7, which is smaller than the target 10. The target cannot be on the left, so move the left boundary past 7.",
            "The new middle value is 10. It matches the target, so return its index: 3.",
        ],
        "ml": [
            "values sorted ആയതിനാൽ ഓരോ item-ഉം പരിശോധിക്കാതെ മുഴുവൻ range-ന്റെ നടുവിൽ നിന്ന് തുടങ്ങുക.",
            "നടുവിലെ മൂല്യം 7 ആണ്; അത് target ആയ 10-നെക്കാൾ ചെറുതാണ്. target ഇടതുവശത്ത് ഇല്ല, അതിനാൽ left boundary 7-ന് ശേഷം മാറ്റുക.",
            "പുതിയ നടുവിലെ മൂല്യം 10 ആണ്. അത് target-നോട് പൊരുത്തപ്പെടുന്നു; അതിനാൽ index 3 മടക്കുക.",
        ],
    },
    "first-lonely-character": {
        "en": [
            "First count every character. A count tells us whether a character appears once or is repeated.",
            "Scan the original text from left to right. At index 1, “w” has count 1, so it is the first lonely character.",
            "Return index 1 immediately. We do not need to inspect later unique characters.",
        ],
        "ml": [
            "ആദ്യം എല്ലാ അക്ഷരങ്ങളും എണ്ണുക. അക്ഷരം ഒരിക്കൽ മാത്രമാണോ ആവർത്തിക്കുന്നുണ്ടോ എന്ന് count പറയുന്നു.",
            "യഥാർത്ഥ ടെക്സ്റ്റ് ഇടത്തുനിന്ന് വലത്തേക്ക് പരിശോധിക്കുക. index 1-ൽ “w” യുടെ count 1 ആണ്; അതാണ് ആദ്യ lonely character.",
            "index 1 ഉടൻ മടക്കുക. പിന്നീട് ഉള്ള unique അക്ഷരങ്ങൾ പരിശോധിക്കേണ്ടതില്ല.",
        ],
    },
    "longest-unique-window": {
        "en": [
            "Grow a window while its characters are all different. “pw” is valid, so the best length is 2.",
            "The next “w” repeats a character already inside the window. Move the left edge just after the old “w” so the window is unique again.",
            "The window “wke” has three different characters. Record 3 as the best length and return it.",
        ],
        "ml": [
            "window-ലുള്ള അക്ഷരങ്ങൾ എല്ലാം വ്യത്യസ്തമായിരിക്കുമ്പോൾ അത് വളർത്തുക. “pw” valid ആയതിനാൽ best length 2 ആണ്.",
            "അടുത്ത “w” window-ലുള്ള അക്ഷരം ആവർത്തിക്കുന്നു. പഴയ “w”-ന്റെ ശേഷം left edge മാറ്റി window വീണ്ടും unique ആക്കുക.",
            "“wke” window-ൽ മൂന്ന് വ്യത്യസ്ത അക്ഷരങ്ങളുണ്ട്. best length ആയി 3 സൂക്ഷിച്ച് മടക്കുക.",
        ],
    },
    "combine-time-ranges": {
        "en": [
            "Sort ranges by their starting time. The first range becomes the first range in our merged answer.",
            "[2, 6] starts before [1, 3] ends, so the ranges overlap. Keep one range and extend its end to 6.",
            "[8, 10] begins after the merged range ends at 6. It cannot join the previous range, so append it separately.",
        ],
        "ml": [
            "ranges-നെ starting time അനുസരിച്ച് sort ചെയ്യുക. ആദ്യ range merged ഉത്തരത്തിലെ ആദ്യ range ആകുന്നു.",
            "[2, 6] ആരംഭിക്കുന്നത് [1, 3] അവസാനിക്കുന്നതിന് മുമ്പാണ്; അതിനാൽ overlap ഉണ്ട്. ഒരു range മാത്രം വെച്ച് end 6 വരെ നീട്ടുക.",
            "[8, 10] ആരംഭിക്കുന്നത് merged range 6-ൽ അവസാനിച്ചതിന് ശേഷമാണ്. അതിനാൽ മുമ്പത്തേതിനോട് ചേർക്കാതെ പ്രത്യേകം append ചെയ്യുക.",
        ],
    },
    "count-land-clusters": {
        "en": [
            "Find a land cell that we have not visited. This starts one new island, so increase the island count.",
            "Use a stack to visit every land neighbour connected to that first cell. Marking them visited prevents counting the same island again.",
            "After scanning the whole grid, three separate connected groups were found, so return 3.",
        ],
        "ml": [
            "ഇതുവരെ സന്ദർശിക്കാത്ത land cell കണ്ടെത്തുക. ഇത് ഒരു പുതിയ island തുടങ്ങുന്നു, അതിനാൽ island count വർധിപ്പിക്കുക.",
            "ആദ്യ cell-നോട് ചേർന്ന ഓരോ land neighbour-നെയും stack ഉപയോഗിച്ച് സന്ദർശിക്കുക. visited ആയി mark ചെയ്യുന്നത് ഒരേ island വീണ്ടും എണ്ണുന്നത് തടയും.",
            "മുഴുവൻ grid പരിശോധിച്ചപ്പോൾ മൂന്ന് വേറിട്ട connected group-ുകൾ ലഭിച്ചു; അതിനാൽ 3 മടക്കുക.",
        ],
    },
    "count-coin-combinations": {
        "en": [
            "There is exactly one way to make amount 0: choose no coins. This is the starting point for dynamic programming.",
            "Process coin 2 and update every amount from 2 upward. Each update adds the ways that were already known for the smaller amount.",
            "After processing all coins, ways[5] is 4. That means four different coin combinations make amount 5.",
        ],
        "ml": [
            "amount 0 ഉണ്ടാക്കാൻ ഒരു വഴിമാത്രമേയുള്ളു: coin ഒന്നും എടുക്കാതിരിക്കുക. ഇത് dynamic programming-ന്റെ തുടക്കമാണ്.",
            "coin 2 process ചെയ്ത് 2 മുതൽ മുകളിലുള്ള ഓരോ amount-ഉം update ചെയ്യുക. ചെറിയ amount-നുള്ള അറിയാവുന്ന വഴികൾ ഓരോ update-ലും ചേർക്കുന്നു.",
            "എല്ലാ coin-ുകളും process ചെയ്തതിന് ശേഷം ways[5] = 4. amount 5 ഉണ്ടാക്കാൻ നാല് വ്യത്യസ്ത combination-ുകൾ ഉണ്ടെന്നർത്ഥം.",
        ],
    },
}


def plain_trace(slug: str, path: dict[str, object]) -> list[dict[str, object]]:
    """Convert authored legacy states to the single player JSON contract.

    New and migrated questions store only flat step objects. The shared React
    player needs no question-specific rendering code: it reads `array`,
    `cursor`, and the two note fields from every row.
    """
    result: list[dict[str, object]] = []
    traces = list(path["trace"])
    notes_en = TRACE_NOTES[slug]["en"]
    notes_ml = TRACE_NOTES[slug]["ml"]
    for index, raw_value in enumerate(traces):
        raw = dict(raw_value)
        state = dict(raw.get("state", {}))
        array = state.get("array") or state.get("values")
        if not isinstance(array, list):
            if isinstance(state.get("text"), str):
                array = list(state["text"])
            elif slug == "add-two-values":
                array = [state.get("a", 3), state.get("b", 8)]
            elif slug == "bracket-check":
                array = state.get("stack_before") or state.get("stack") or [state.get("character", "")]
            elif slug == "combine-time-ranges":
                array = state.get("sorted_ranges") or state.get("merged") or []
            elif slug == "count-land-clusters":
                array = state.get("visited") or state.get("stack") or []
            elif slug == "count-coin-combinations":
                array = state.get("ways") or []
            else:
                array = []
        cursor = state.get("cursor", state.get("index", state.get("middle", state.get("left"))))
        if not isinstance(cursor, int) or cursor < 0:
            cursor = min(index, len(array) - 1) if array else 0
        context = {
            key: value
            for key, value in state.items()
            if key not in {"array", "values", "text", "cursor", "index", "middle", "left"}
        }
        result.append(
            {
                "step": int(raw.get("step", index + 1)),
                "array": array,
                "cursor": cursor,
                "note_en": notes_en[index],
                "note_ml": str(notes_ml[index]),
                **context,
            }
        )
    return result
