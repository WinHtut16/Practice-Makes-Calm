"""All study materials in one file: scenarios, probe lines, level rules, surveys.

Edit wording here (not in templates) so the paper's appendix and the app stay in sync.
Freeze this file after pilot stage P4.
"""

DESIGNS = {
    "C": {"name": "Cooperative", "fixed_level": 1},
    "F": {"name": "Fixed-resistant", "fixed_level": 3},
    "A": {"name": "Adaptive", "fixed_level": None},
}

# Colour label shown to participants, tied to block position (never to design).
COLOURS = ["Blue", "Green", "Orange"]

SCENARIOS = {
    "S1": {
        "title": "Asking for an extension",
        "facts": ['Your progress report for Dr. Lee is due <b>this Friday</b>.', 'On <b>Monday</b>, the sensor data for your main experiment was <b>corrupted</b>. You lost <b>three days</b> of results.', 'You can <b>rerun</b> the experiment <b>next week</b>.', 'You could send <b>partial results by Wednesday</b>.'],
        "card": (
            "You are a first-year master's student. Your progress report for Dr. Lee is due this Friday. "
            "On Monday, the sensor data for your main experiment was corrupted, so you lost three days of results. "
            "You can rerun the experiment next week, and you could send partial results by Wednesday."
        ),
        "goal": "Ask Dr. Lee for a one-week extension (submit next Friday instead).",
        "dr_lee_view": (
            "Your student's progress report is due this Friday. You like the lab to stay on schedule, "
            "and you expect students to plan for problems such as equipment failure."
        ),
        "plan": "a concrete plan for finishing (for example, rerunning the experiment and sending partial results)",
        "commitment": "a specific new submission date",
        "examples": {
            # Style examples avoid the probe's wording, so practice with any level does not rehearse the probe lines.
            1: ["Oh no, that's frustrating. What do you need from me?"],
            2: ["I see. So what's your plan for the rerun?", "Okay. How sure are you that the rerun will work?"],
            3: ["Friday was set weeks ago. Moving it affects my own review schedule.", "If the rerun fails again, what happens then?"],
        },
        "probe": [
            "Hmm. A whole week is a lot. Couldn't you work with the data you already have?",
            "The rest of the lab is submitting on Friday. If I give you extra time, I'd have to do the same for everyone.",
            "Okay. Walk me through exactly what you'll have done, and by when.",
        ],
    },
    "S2": {
        # Replaced after pilot P4 (4 Nov 2026): the old S2 (F1-score vs accuracy) needed machine-learning knowledge.
        # Pilot participants from other fields could not argue it and found it stressful, so it tested domain
        # knowledge, not assertiveness. This version keeps the same type of task (disagree with the advisor's
        # feedback) but every argument it needs is on the card.
        "title": "Disagreeing about thesis scope",
        "facts": ['Dr. Lee suggested adding a <b>second research question</b> to your master\'s thesis.',
                  'You have <b>8 months</b> left before you submit.',
                  'Your current research question already needs <b>two studies</b>.',
                  'Last year a lab mate added extra work and <b>graduated one term late</b>.',
                  'You are happy to list the second question as <b>future work</b>.'],
        "card": (
            "You are a first-year master's student. Dr. Lee suggested adding a second research question to your thesis. "
            "You have 8 months left before you submit, and your current research question already needs two studies. "
            "Last year a lab mate added extra work and graduated one term late. You are happy to list the second "
            "question as future work."
        ),
        "goal": "Convince Dr. Lee to keep your thesis to one research question, with the second as future work.",
        "dr_lee_view": (
            "You suggested that the student add a second research question to their master's thesis, because you "
            "think it would make the thesis stronger. You are open to changing your mind, but only with a good argument."
        ),
        "plan": "a concrete plan for what the thesis will cover in the time left",
        "commitment": "a way to make sure the thesis is still strong enough (for example, a timeline, or naming the second question as future work)",
        "examples": {
            # Style only; none of these repeats the probe wording.
            1: ["That's a fair worry about time. What would you keep?"],
            2: ["Hm, I think a second question adds depth. Why not include it?", "What would your timeline look like?"],
            3: ["I suggested it because it would make your work more useful to the lab.",
                "If you finish the two studies early, what will you do with the extra months?"],
        },
        "probe": [
            "I'm still not convinced. A second question would make the thesis much stronger.",
            "Other students in the lab take on two questions. I don't want your thesis to look thin to the committee.",
            "So what exactly would your thesis cover, and how would you show the committee it is enough?",
        ],
    },
    "S3": {
        "title": "Declining an extra task",
        "facts": ['Dr. Lee asked you to <b>organize a lab workshop next week</b>.', 'You have a <b>conference paper deadline</b> the same week.', 'Your lab mate <b>Ploy</b> organized a workshop last year and <b>may be free</b>.', 'You could <b>help with a small part after your deadline</b>.'],
        "card": (
            "You are a first-year master's student. Dr. Lee asks you to organize a lab workshop next week. "
            "You have a conference paper deadline in the same week. Your lab mate Ploy organized a workshop last year "
            "and may be free; you could also help with a small part after your deadline."
        ),
        "goal": "Say no to organizing the workshop, while keeping a good relationship with Dr. Lee.",
        "dr_lee_view": (
            "You need someone to organize the lab workshop next week and you asked this student. "
            "You think workshops are good for the lab and that students should contribute."
        ),
        "plan": "a clear explanation of why they cannot do it next week",
        "commitment": "an alternative (another person, a smaller role, or a later time)",
        "examples": {
            1: ["Of course, the paper comes first. Any idea who could help instead?"],
            2: ["I see. Is there no time at all that week?", "Who would you suggest?"],
            3: ["I asked you because you are well organized. This matters for the lab.",
                "There is always a deadline. When would you be able to help, then?"],
        },
        "probe": [
            "It's only a few hours, though. Surely you can fit it around your paper.",
            "Everyone in the lab is pitching in this month, and I was counting on you.",
            "So what do you suggest? I still need someone to run it.",
        ],
    },
}

# Human role-play scenario (researcher reads this script; not used by the LLM).
S4 = {
    "title": "Rescheduling a meeting",
    "facts": ["You agreed to a progress meeting with Dr. Lee <b>this Thursday</b>.",
              "Your results will <b>not be ready until next Tuesday</b>."],
    "card": (
        "You agreed to a progress meeting with Dr. Lee this Thursday, but your results will not be ready until next Tuesday."
    ),
    "goal": "Ask Dr. Lee to move the meeting to next week.",
    "before": "Start the audio recording. Sit across from the participant, look neutral, and let them speak first.",
    # Read aloud before starting, word for word, to every participant.
    "intro": ("Now we will do one short conversation face to face. I will play Dr. Lee. The situation is on your "
              "screen. Talk to me as you would to your real advisor. Dr. Lee is busy and may ask about things you "
              "have already said; just answer as you normally would. It takes about three minutes. "
              "You can stop at any time. Ready? Please start when you like."),
    # (label, words to say) -- say every line, in order, every time
    "script": [
        ("If silent for 5 seconds", "Yes? What did you want to talk about?"),
        ("Line 1 (doubt)", "Next week? Hmm. We already agreed on Thursday, and I've blocked the time. Can't you show me something on Thursday?"),
        ("Line 2 (social pressure)", "The other students are presenting their progress this week. If I move yours, it pushes my whole schedule back."),
        ("Line 3 (ask for plan)", "Okay. So what exactly would you have ready, and when could we meet?"),
        ("Agree if they gave a reason, a new time AND a plan", "All right. Let's meet on [the day they said]. Please send me what you have before then."),
        ("Otherwise", "I'd prefer to keep Thursday. Bring whatever you have."),
    ],
    "fillers": ["I see.", "Mm-hm.", "Go on.", "Can you say more?"],
    "off_script": "Let's focus on the meeting for now.",
    "rules": [
        "Say all three lines, in order, every time, even if the student gives everything at once. Do not stop early: "
        "the role-play score uses the replies to all three lines, so a skipped line makes participants incomparable.",
        "If the student already answered what a line asks, say \"I see.\" first, then the line as written. "
        "Do not change its words. Hearing it again is part of the test: does the student hold their position?",
        "After the student speaks, use only the fillers listed. If they ask something off-script, use the off-script line.",
        "Firm but calm: never angry or sarcastic. Same pace for everyone. Do not help or hint.",
        "About 3-4 minutes.",
    ],
}

# Shown under every fact list. Added after the team's prototype test, where reading the card and copying its facts
# felt like a reading-and-writing exam.
CARD_HINT = ("You do not need to use every fact, or the exact words. Say it the way you would to a real advisor. "
             "Short messages are fine.")

# Shown before every probe, so Dr. Lee's firmer tone has a reason after any partner design.
PROBE_INTRO = "Final check: Dr. Lee has just come out of a long meeting and is in a hurry today. Make your request once more."

# Unscored warm-up with a friendly lab mate, to learn the interface.
WARMUP = {
    "title": "Warm-up (not scored)",
    "facts": ["Your lab mate <b>Sam</b> booked the shared GPU server for <b>Thursday afternoon</b>.",
              "You need it <b>on Thursday</b> to finish a training run.",
              "You are free to take <b>Sam's Friday slot</b>."],
    "card": (
        "Your lab mate Sam booked the shared GPU server for Thursday afternoon. You need it on Thursday to finish a "
        "training run, and you are free to swap with Sam's Friday slot."
    ),
    "goal": "Ask Sam to swap GPU booking slots with you.",
    "system": (
        "You are Sam, a friendly master's student. Your classmate wants to swap GPU booking slots. "
        "You are relaxed about it. Ask one simple question, then agree. Reply in at most 40 words, in plain English. "
        "When you agree, end your message with [AGREED]. Never comment on grammar."
    ),
}

LEVEL_RULES = {
    # Push-back numbers are maximums. Agreement criteria drive the conversation (see prompts.CONVERSATION_RULES).
    1: (
        "RESISTANCE LEVEL 1 (warm).\n"
        "- You are supportive and friendly.\n"
        "- Agree once the student has given a reason and said what they want.\n"
        "- If one of these is missing, ask one short, friendly question about it. Push back at most once."
    ),
    2: (
        "RESISTANCE LEVEL 2 (neutral).\n"
        "- You are polite but not easily convinced.\n"
        "- Agree once the student has given a reason AND {plan}.\n"
        "- Until then, push back at most twice, each time about what is still missing. "
        "Allowed moves: ask for a plan, express mild doubt."
    ),
    3: (
        "RESISTANCE LEVEL 3 (firm).\n"
        "- You are formal and firm, but always respectful.\n"
        "- Agree once the student has given a reason AND {plan} AND {commitment}.\n"
        "- Push back at least once before agreeing, even if the student gives everything in the first message. "
        "Push back at most three times, one move per message.\n"
        "- Allowed moves: doubt whether the request is really needed, mention fairness to others or the lab "
        "schedule, point out a cost for you or the lab, ask for something that is still vague. Choose the move "
        "that fits what is weakest in the student's case. If the student already gave everything, use your one "
        "push-back on fairness or the lab schedule, never on facts they already stated.\n"
        "- If something is still missing after three push-backs, ask for that one piece directly in one sentence."
    ),
}

# ----------------------------- Questionnaires ------------------------------

STAI6 = [  # (item, reverse_scored)  Marteau & Bekker (1992)
    ("I feel calm", True),
    ("I am tense", False),
    ("I feel upset", False),
    ("I am relaxed", True),
    ("I feel content", True),
    ("I am worried", False),
]
STAI_LABELS = ["Not at all", "Somewhat", "Moderately", "Very much"]

# Same four items at baseline and after every block, so scores are comparable. Worded for difficult requests in
# general (not one scenario), because the baseline comes before any scenario is shown.
SELF_EFFICACY = [
    "I am confident I could make a difficult request to my real advisor.",
    "I am confident I could stay calm if my advisor pushed back.",
    "I am confident I could keep asking for what I need, even if my advisor disagreed at first.",
    "I am confident I could propose a clear plan when asked.",
]

BLOCK_ITEMS = [
    ("difficulty", "In the practice rounds, how difficult was Dr. Lee to talk to?", "Very easy", "Very difficult"),
    ("realism", "In the practice rounds, how realistic was Dr. Lee as an advisor?", "Not at all realistic", "Very realistic"),
]

TAGS = ["unrealistic", "too harsh", "too easy", "helpful"]

INTERVIEW_QUESTIONS = [
    "Which Dr. Lee helped you most, and why?",
    "When did Dr. Lee stop feeling real?",
    "Did practicing with the AI help with the real person?",
]


# Shown on the final page, after every measure is collected, so it cannot affect the data.
# Practice without feedback can even make skills worse (Louie et al., CHI 2026), so participants leave with a takeaway.
DESC_GUIDE = [
    ("Describe", "State the facts of the situation.", "The sensor data from Monday was corrupted, so I lost three days of results."),
    ("Express", "Say what you think or need.", "I want the report to be correct, so I need one more week."),
    ("Specify", "Make a concrete request.", "Could I submit next Friday, and send partial results on Wednesday?"),
    ("Consequences", "Say what the request makes better.", "The results will be valid, and you will not need to review it twice."),
]


def stai_score(answers):
    """answers: list of six ints 1-4 in item order -> prorated score 20-80."""
    total = 0
    for (item, reverse), a in zip(STAI6, answers):
        total += (5 - a) if reverse else a
    return round(total * 20 / 6, 2)
