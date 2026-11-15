"""Deterministic subsequence scoring, without dependencies or external tools."""


def fuzzy_score(query, text):
    query, text = query.casefold(), text.casefold()
    total = 0
    for word in query.split():
        previous = -1
        for character in word:
            position = text.find(character, previous + 1)
            if position < 0:
                return None
            total += position if previous < 0 else (position - previous - 1) * 3
            if position == 0 or not text[position - 1].isalnum():
                total -= 2
            previous = position
    return total
