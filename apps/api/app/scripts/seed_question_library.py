"""Seed a small original, ready-to-schedule Codele question library.

The challenges use common interview concepts, but their titles and wording are
written for Codele rather than copied from any third-party problem library.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.models import (
    Category,
    Level,
    Question,
    QuestionHint,
    QuestionVersion,
    QuestionVersionStatus,
    TestCase,
    TestVisibility,
    User,
    UserRole,
)
from app.db.session import SessionLocal
from app.scripts.question_learning_paths import LEARNING_PATHS, plain_trace


def challenge(
    slug: str,
    title: str,
    level: Level,
    topic: str,
    difficulty: int,
    statement: str,
    public_input: object,
    public_output: object,
    hidden_input: object,
    hidden_output: object,
    python: str,
    javascript: str,
    hints: list[str],
    complexity: str,
) -> dict[str, object]:
    return {
        "slug": slug,
        "title": title,
        "level": level,
        "topic": topic,
        "difficulty": difficulty,
        "statement": statement,
        "public_input": public_input,
        "public_output": public_output,
        "hidden_input": hidden_input,
        "hidden_output": hidden_output,
        "python": python,
        "javascript": javascript,
        "hints": hints,
        "complexity": complexity,
    }


CHALLENGES = [
    challenge(
        "add-two-values", "Add Two Values", Level.ROOKIE, "Fundamentals", 1,
        "Write `solve(a, b)` and return the sum of the two integer values.", [3, 8], 11,
        [-12, 7], -5, "def solve(a, b):\n    # Return the sum.\n    pass",
        "function solve(a, b) {\n  // Return the sum.\n}",
        ["The plus operator combines two numbers.", "No loop is needed.", "Return the expression, do not print it."],
        "Time O(1), space O(1).",
    ),
    challenge(
        "mirror-a-message", "Mirror a Message", Level.ROOKIE, "Strings", 1,
        "Write `solve(text)` to return the characters in `text` in reverse order.", "code", "edoc",
        "racecar", "racecar", "def solve(text):\n    # Return reversed text.\n    pass",
        "function solve(text) {\n  // Return reversed text.\n}",
        ["Strings can be sliced from the end.", "Do not change letter case.", "An empty string should return an empty string."],
        "Time O(n), space O(n) for the returned text.",
    ),
    challenge(
        "count-the-vowels", "Count the Vowels", Level.ROOKIE, "Strings", 2,
        "Write `solve(text)` to count English vowels (`a`, `e`, `i`, `o`, `u`) in text, ignoring case.",
        "Codele", 3, "Rhythm and Blues", 3, "def solve(text):\n    # Count vowels ignoring case.\n    pass",
        "function solve(text) {\n  // Count vowels ignoring case.\n}",
        ["Convert the text to one case first.", "Keep the vowels in a set or string.", "Check each character once."],
        "Time O(n), space O(1).",
    ),
    challenge(
        "bracket-check", "Bracket Check", Level.ROOKIE, "Stacks", 2,
        "Write `solve(text)` to return true only when parentheses, square brackets, and braces are correctly balanced.",
        "{[()]}", True, "([)]", False, "def solve(text):\n    # Return True for balanced brackets.\n    pass",
        "function solve(text) {\n  // Return true for balanced brackets.\n}",
        ["Opening symbols must be remembered until they close.", "A list can act as a stack.", "Every closing symbol must match the latest opening symbol."],
        "Time O(n), space O(n).",
    ),
    challenge(
        "find-in-sorted-list", "Find in a Sorted List", Level.HACKER, "Searching", 2,
        "Write `solve(values, target)` to return the index of target in ascending `values`, or -1 when it is absent.",
        [[1, 4, 7, 10, 15], 10], 3, [[2, 5, 9, 14], 8], -1,
        "def solve(values, target):\n    # Search values efficiently.\n    pass",
        "function solve(values, target) {\n  // Search values efficiently.\n}",
        ["The list is already sorted.", "Compare the target with the middle value.", "Discard half of the remaining range after each comparison."],
        "Time O(log n), space O(1).",
    ),
    challenge(
        "first-lonely-character", "First Lonely Character", Level.HACKER, "Hash Maps", 2,
        "Write `solve(text)` to return the index of the first character that occurs exactly once, or -1 if there is none.",
        "swiss", 1, "aabbcc", -1, "def solve(text):\n    # Find the first non-repeated character.\n    pass",
        "function solve(text) {\n  // Find the first non-repeated character.\n}",
        ["Count every character first.", "A dictionary or map stores counts.", "Make a second pass in original order."],
        "Time O(n), space O(k), where k is the character set size.",
    ),
    challenge(
        "longest-unique-window", "Longest Unique Window", Level.HACKER, "Sliding Window", 3,
        "Write `solve(text)` to return the length of the longest substring containing no repeated characters.",
        "pwwkew", 3, "abba", 2, "def solve(text):\n    # Return the longest unique substring length.\n    pass",
        "function solve(text) {\n  // Return the longest unique substring length.\n}",
        ["Use two indexes to represent a window.", "Track the last position of each character.", "Move the left edge only forward."],
        "Time O(n), space O(k).",
    ),
    challenge(
        "combine-time-ranges", "Combine Time Ranges", Level.HACKER, "Intervals", 3,
        "Write `solve(ranges)` to merge overlapping inclusive ranges. Return ranges sorted by their starting value.",
        [[[1, 3], [2, 6], [8, 10]]], [[1, 6], [8, 10]], [[[1, 4], [4, 5], [10, 12]]], [[1, 5], [10, 12]],
        "def solve(ranges):\n    # Merge overlapping ranges.\n    pass",
        "function solve(ranges) {\n  // Merge overlapping ranges.\n}",
        ["Sort ranges by their first value.", "Compare each range with the most recently merged range.", "If they overlap, extend the end instead of adding another range."],
        "Time O(n log n) due to sorting, space O(n) for output.",
    ),
    challenge(
        "count-land-clusters", "Count Land Clusters", Level.ARCHITECT, "Graphs", 4,
        "Write `solve(grid)` to count connected groups of `1` cells. Cells connect horizontally and vertically; `0` is water.",
        [[["1", "1", "0"], ["0", "1", "0"], ["1", "0", "1"]]], 3,
        [[["1", "0", "1"], ["0", "0", "0"], ["1", "1", "0"]]], 3,
        "def solve(grid):\n    # Count four-direction land clusters.\n    pass",
        "function solve(grid) {\n  // Count four-direction land clusters.\n}",
        ["Visit one land cell and mark its whole connected component.", "Depth-first search or breadth-first search both work.", "Keep a set of visited row and column pairs."],
        "Time O(rows × columns), space O(rows × columns) in the worst case.",
    ),
    challenge(
        "count-coin-combinations", "Count Coin Combinations", Level.ARCHITECT, "Dynamic Programming", 4,
        "Write `solve(amount, coins)` to return how many combinations make `amount`. Coin order must not create a new combination.",
        [5, [1, 2, 5]], 4, [3, [2]], 0, "def solve(amount, coins):\n    # Count unordered coin combinations.\n    pass",
        "function solve(amount, coins) {\n  // Count unordered coin combinations.\n}",
        ["Start with one way to make amount zero.", "Process one coin value at a time.", "For each coin, update amounts from that coin up to the target."],
        "Time O(amount × number of coins), space O(amount).",
    ),
]


SOLUTIONS = {
    "add-two-values": ("def solve(a, b):\n    return a + b", "function solve(a, b) { return a + b; }"),
    "mirror-a-message": ("def solve(text):\n    return text[::-1]", "function solve(text) { return [...text].reverse().join(''); }"),
    "count-the-vowels": ("def solve(text):\n    return sum(char.lower() in 'aeiou' for char in text)", "function solve(text) { return [...text].filter(char => 'aeiou'.includes(char.toLowerCase())).length; }"),
    "bracket-check": ("def solve(text):\n    pairs = {')': '(', ']': '[', '}': '{'}\n    stack = []\n    for char in text:\n        if char in '([{': stack.append(char)\n        elif char in pairs:\n            if not stack or stack.pop() != pairs[char]: return False\n    return not stack", "function solve(text) { const pairs = { ')': '(', ']': '[', '}': '{' }; const stack = []; for (const char of text) { if ('([{'.includes(char)) stack.push(char); else if (pairs[char] && (!stack.length || stack.pop() !== pairs[char])) return false; } return !stack.length; }"),
    "find-in-sorted-list": ("def solve(values, target):\n    left, right = 0, len(values) - 1\n    while left <= right:\n        middle = (left + right) // 2\n        if values[middle] == target: return middle\n        if values[middle] < target: left = middle + 1\n        else: right = middle - 1\n    return -1", "function solve(values, target) { let left = 0, right = values.length - 1; while (left <= right) { const middle = Math.floor((left + right) / 2); if (values[middle] === target) return middle; if (values[middle] < target) left = middle + 1; else right = middle - 1; } return -1; }"),
    "first-lonely-character": ("def solve(text):\n    counts = {}\n    for char in text: counts[char] = counts.get(char, 0) + 1\n    for index, char in enumerate(text):\n        if counts[char] == 1: return index\n    return -1", "function solve(text) { const counts = {}; for (const char of text) counts[char] = (counts[char] || 0) + 1; return [...text].findIndex(char => counts[char] === 1); }"),
    "longest-unique-window": ("def solve(text):\n    last, left, best = {}, 0, 0\n    for right, char in enumerate(text):\n        if char in last and last[char] >= left: left = last[char] + 1\n        last[char] = right\n        best = max(best, right - left + 1)\n    return best", "function solve(text) { const last = new Map(); let left = 0, best = 0; for (let right = 0; right < text.length; right += 1) { const char = text[right]; if (last.has(char) && last.get(char) >= left) left = last.get(char) + 1; last.set(char, right); best = Math.max(best, right - left + 1); } return best; }"),
    "combine-time-ranges": ("def solve(ranges):\n    if not ranges: return []\n    merged = [sorted(ranges)[0]]\n    for start, end in sorted(ranges)[1:]:\n        if start <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], end)\n        else: merged.append([start, end])\n    return merged", "function solve(ranges) { if (!ranges.length) return []; const sorted = ranges.map(range => [...range]).sort((a, b) => a[0] - b[0]); const merged = [sorted[0]]; for (const [start, end] of sorted.slice(1)) { const last = merged[merged.length - 1]; if (start <= last[1]) last[1] = Math.max(last[1], end); else merged.push([start, end]); } return merged; }"),
    "count-land-clusters": ("def solve(grid):\n    seen, total = set(), 0\n    for row in range(len(grid)):\n        for col in range(len(grid[row])):\n            if grid[row][col] != '1' or (row, col) in seen: continue\n            total += 1; stack = [(row, col)]; seen.add((row, col))\n            while stack:\n                r, c = stack.pop()\n                for nr, nc in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):\n                    if 0 <= nr < len(grid) and 0 <= nc < len(grid[nr]) and grid[nr][nc] == '1' and (nr,nc) not in seen:\n                        seen.add((nr,nc)); stack.append((nr,nc))\n    return total", "function solve(grid) { const seen = new Set(); let total = 0; for (let r = 0; r < grid.length; r += 1) for (let c = 0; c < grid[r].length; c += 1) { const key = `${r},${c}`; if (grid[r][c] !== '1' || seen.has(key)) continue; total += 1; const stack = [[r, c]]; seen.add(key); while (stack.length) { const [row, col] = stack.pop(); for (const [nr, nc] of [[row+1,col],[row-1,col],[row,col+1],[row,col-1]]) { const next = `${nr},${nc}`; if (nr >= 0 && nr < grid.length && nc >= 0 && nc < grid[nr].length && grid[nr][nc] === '1' && !seen.has(next)) { seen.add(next); stack.push([nr, nc]); } } } } return total; }"),
    "count-coin-combinations": ("def solve(amount, coins):\n    ways = [0] * (amount + 1); ways[0] = 1\n    for coin in coins:\n        for value in range(coin, amount + 1): ways[value] += ways[value - coin]\n    return ways[amount]", "function solve(amount, coins) { const ways = Array(amount + 1).fill(0); ways[0] = 1; for (const coin of coins) for (let value = coin; value <= amount; value += 1) ways[value] += ways[value - coin]; return ways[amount]; }"),
}


def main() -> None:
    with SessionLocal() as session:
        author = session.scalar(
            select(User).where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
        )
        if author is None:
            raise SystemExit("Create an admin account before seeding the question library.")
        existing_slugs = set(session.scalars(select(Question.slug)))
        categories = {category.name: category for category in session.scalars(select(Category))}
        created = 0
        for item in CHALLENGES:
            slug = item["slug"]
            if slug in existing_slugs:
                continue
            category = categories.get(item["topic"])
            if category is None:
                category = Category(
                    name=item["topic"],
                    slug=str(item["topic"]).lower().replace(" ", "-"),
                )
                session.add(category)
                session.flush()
                categories[category.name] = category
            python_solution, javascript_solution = SOLUTIONS[slug]
            learning_path = LEARNING_PATHS[slug]
            question = Question(slug=slug)
            version = QuestionVersion(
                question=question, version_number=1, title=item["title"], statement_markdown=item["statement"],
                examples=[{"input": item["public_input"], "output": item["public_output"]}],
                category_id=category.id, level=item["level"], topic=category.name, difficulty=item["difficulty"],
                starter_code={"python": item["python"], "javascript": item["javascript"]},
                solution_code={"python": python_solution, "javascript": javascript_solution},
                explanation_markdown="The reference solution follows the intended core data structure or algorithm.",
                explanation_en=str(learning_path["en"]), explanation_ml=str(learning_path["ml"]),
                solution_trace=plain_trace(slug, learning_path),
                solution_notes_en=list(learning_path["notes_en"]),
                solution_notes_ml=list(learning_path["notes_ml"]),
                complexity_notes=item["complexity"], status=QuestionVersionStatus.READY, created_by_id=author.id,
                alternative_approaches=[{
                    "title": "Baseline approach",
                    "summary_markdown": "Start with a direct implementation, then improve it by applying the intended data structure or algorithm.",
                    "time_complexity": "Depends on input size",
                    "space_complexity": "Depends on input size",
                }],
            )
            session.add_all([question, version])
            session.add_all([
                TestCase(question_version=version, position=1, visibility=TestVisibility.PUBLIC, input_data=item["public_input"], expected_output=item["public_output"], explanation="Public example."),
                TestCase(question_version=version, position=2, visibility=TestVisibility.HIDDEN, input_data=item["hidden_input"], expected_output=item["hidden_output"], explanation="Hidden edge case."),
            ])
            session.add_all([QuestionHint(question_version=version, position=index, content_markdown=hint, xp_penalty=0) for index, hint in enumerate(item["hints"], start=1)])
            created += 1
        session.commit()
    print(f"Added {created} ready-to-schedule Codele questions; skipped existing slugs.")


if __name__ == "__main__":
    main()
