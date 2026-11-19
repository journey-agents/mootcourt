"""The fixed protocol of the simulated readers: seed, random streams, models and sizes. Fixed before any model call."""
from __future__ import annotations

import numpy as np

SEED = 20261118
STREAMS = {"blocks": 1, "arms": 2, "positions": 3, "probe_set": 4, "examples": 5, "brief_draw": 6, "bootstrap": 7,
           "probe_items": 8}

MODELS = ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5")
PRIMARY_MODEL = MODELS[0]

BLOCK_SIZE = 30
N_READERS = 10
HALVES = ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10))
CELL = "headline_only"
Z = 1.96


def rng(stream: str, *keys: int) -> np.random.Generator:
    """The generator of one named stream and its integer keys. Each draw of the protocol has its own."""
    return np.random.default_rng([SEED, STREAMS[stream], *(int(k) for k in keys)])

# The reader's instructions. The profile and the feed arrive in the prompt; this text is the same for every call.
SYSTEM_PROMPT = (
    "You are playing one person who is browsing the web at some time between 2013 and 2015. You will be given a short "
    "description of that person and then a feed of story headlines from a news and entertainment site, numbered, one per "
    "line. For each headline, give the probability from 0 to 100 that this person would click on it at this moment. Judge "
    "each headline as this person would on a quick scroll. Most people click on few of the stories they scroll past. Reply "
    "with one JSON object and nothing else."
)

# ``{profile}``, ``{feed}`` and ``{n}`` are replaced; the braces around "clicks" are part of the copy.
READER_TEMPLATE = (
    "The reader: {profile}\n"
    "\n"
    "The feed:\n"
    "{feed}\n"
    "\n"
    'Reply as {"clicks": [...]} with exactly {n} numbers, one for each headline in order, each from 0 to 100.'
)

# Reader 1 to reader 10. Each varies age band, occupation, interests, mood, device and referral.
PROFILES = (
    "You are between 19 and 24 and a college student. You like music, campus politics and funny videos. You are putting off "
    "an assignment and are a little bored. You are on your phone, and a friend shared this in your social feed.",
    "You are between 25 and 34 and work in an office. You follow national news, technology and personal finance. You are on "
    "a short lunch break and want something quick. You are at your desktop, and the story came up in your social feed.",
    "You are between 25 and 34 and have two small children. You care about parenting, health and stories that end well. It "
    "is late in the evening and you are tired. You are on your phone, and a relative shared this in your social feed.",
    "You are between 35 and 44 and teach at a public school. You care about education, science and your local community. "
    "You are relaxed after dinner. You are at your desktop, and the story arrived in an email newsletter from the site.",
    "You are between 35 and 44 and work as a nurse. You like stories about health, animals and ordinary people. You have "
    "five minutes of a break and are in a hurry. You are on your phone, and the story came up in your social feed.",
    "You are between 45 and 54 and manage a small business. You follow the economy, politics and sports. You are sceptical "
    "of anything that sounds exaggerated. You are at your desktop, and someone you follow posted the link.",
    "You are between 45 and 54 and at home with two teenagers. You care about family, faith and cooking. You are unhurried "
    "and in a good mood. You are at your desktop, and a neighbour shared this in your social feed.",
    "You are between 55 and 64 and recently retired. You like gardening, history and news about your grandchildren's "
    "generation. You have plenty of time. You are at your desktop, and a friend forwarded the story by email.",
    "You are between 18 and 24 and work shifts in a shop. You like celebrities, video games and comedy. You are restless "
    "and scrolling fast. You are on your phone, and the story came up in your social feed.",
    "You are between 25 and 34 and work for a charity. You care about the environment, equal rights and documentaries. You "
    "are curious and willing to read something serious. You are on your phone, and you are on the site's front page.",
)

# Method 6: earlier results shown before the feed.
EXAMPLES_HEADER = ("Results of earlier tests on this site. Each line is a headline and the share of visitors who clicked it. "
                   "Headlines under one number were shown for the same story.")

# Method 7: the model writes a note on the audience from earlier results, and every reader of the origin receives it.
BRIEF_SYSTEM = ("You study the audience of a news and entertainment site from the results of its headline tests. Reply with "
                "one JSON object and nothing else.")
BRIEF_TEMPLATE = (
    "Below are results of earlier headline tests on this site. Headlines under one number were shown for the same story, and "
    "each has the share of visitors who clicked it.\n"
    "\n"
    "{units}\n"
    "\n"
    "Write a note of at most 150 words on what this audience clicked and what it passed over. Describe patterns only. Do not "
    'quote a headline. Reply as {"note": "..."}.'
)
BRIEF_PREFACE = "What is known about this site's audience from earlier tests: {note}"
N_EXAMPLES = 10
N_BRIEF_UNITS = 200
NOTE_WORDS = 150
